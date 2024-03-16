#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  2 16:37:47 2024

@author: setthakorntanom
"""

from datamodel import OrderDepth, UserId, TradingState, Order
import numpy as np
import pandas as pd
import math
from typing import List
import string
import jsonpickle as jp

class Trader:
    
    def run(self, state: TradingState):
        """
        Only method required. It takes all buy and sell orders for all symbols as an input,
        and outputs a list of orders to be sent
        """
        #print("traderData: " + state.traderData)
        #print("Observations: " + str(state.observations))
        #print("Position : " + str(state.position))

		# Orders to be placed on exchange matching engine
        result = {}
        
        window = 200
        if state.traderData == '':
            dfTrader = pd.DataFrame(np.nan, index = range(window), columns = ['mid_price','return'])
        else:
            traderData = jp.decode(state.traderData)
            dfTrader = pd.DataFrame.from_dict(traderData)

        order_depth: OrderDepth = state.order_depths['STARFRUIT']

        data = dfTrader

        # Initialize the list of Orders to be sent as an empty list
        orders: List[Order] = []
        # Define a fair value for the PRODUCT. Might be different for each tradable item
        # Note that this value of 10 is just a dummy value, you should likely change it!
        
        
        if len(order_depth.sell_orders) != 0:
            best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
            isSellOrder = True
            
        if len(order_depth.buy_orders) != 0:
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
            isBuyOrder = True
            
        if isSellOrder and  isBuyOrder:
            mid_price = (best_ask + best_bid)/2
            
        else:
            mid_price = data['mid_price'].iloc[-1]
            
            
        
        data['mid_price'] = data['mid_price'].shift(-1)
        data['mid_price'].iloc[-1] = mid_price
        
        data['return'] = data['mid_price'].pct_change()
        data.loc[data.index[0],'return'] = 0
        
        
        result['AMETHYSTS'] = []
        result['STARFRUIT'] = []
            
        #if not np.any(np.isnan(data['mid_price'])):
        if not np.any(np.isnan(data['mid_price'])):
            
            
            lamb_return = 0.995
            weights_return = Trader.weights(lamb_return,window)
            ewma_return = np.inner(data['return'],weights_return)
            prev_ewma_return = np.inner(data['return'][:-1],weights_return[:-1])
            print('ewma_return:', ewma_return)
            print('prev_ewma_return:', prev_ewma_return)
            
            lamb_sig2 = 0.97
            weights_sig2 = Trader.weights(lamb_sig2,window)
            ewma_sig2 = np.inner(data['return']**2,weights_sig2)
            print('ewma_sig2:', ewma_sig2)
            
            projected_mid = (1+prev_ewma_return)*data.iloc[-2]['mid_price']
            print('projected_mid:', projected_mid)
            
            momentum = ewma_return/math.sqrt(ewma_sig2)   
            print('Momentum:', momentum)
            target_position = 40*math.exp(20*momentum)/(1+math.exp(20*momentum)) -20
            print('Target:',target_position)
            current_position = state.position.get('STARFRUIT',0)
            print('Current:',current_position)
            adjust_position = target_position-current_position
            
            #if adjust_position > 3.5:
                #adjust_position = math.floor(target_position-current_position)
            #elif adjust_position < -3.5:
                #adjust_position = math.ceil(target_position-current_position)
            #else:
                #adjust_position = 0
            
            print('Adjust:',adjust_position)
            

            
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                print('Best_Ask:', best_ask)

                if best_ask < projected_mid:
                    signal = (projected_mid-best_ask)/(projected_mid*math.sqrt(ewma_sig2))
                    print('signal:', signal)
                    volume = math.floor(40*math.exp(1.5*signal)/(1+math.exp(1.5*signal)) -20)
                    ceil_volume = min(volume,20-current_position)
                    orders.append(Order('STARFRUIT', best_ask, ceil_volume))
                    print('Long:', ceil_volume)
                    
                
    
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                print('Best_Bid:', best_bid)
                    
                if best_bid > projected_mid:
                    signal = (projected_mid-best_bid)/(projected_mid*math.sqrt(ewma_sig2))
                    print('signal:', signal)
                    volume = math.ceil(40*math.exp(1.5*signal)/(1+math.exp(1.5*signal)) -20)
                    floor_volume = max(volume,-current_position-20)
                    orders.append(Order('STARFRUIT', best_bid, floor_volume))
                    print('Short:', floor_volume)
                
            
            result['AMETHYSTS'] = []
            result['STARFRUIT'] = orders
    
        dfTrader = data
		# String value holding Trader state data required. 
		# It will be delivered as TradingState.traderData on next execution.
        traderData = dfTrader.to_dict()
        traderDataEncoded = jp.encode(traderData)
        
		# Sample conversion request. Check more details below. 
        conversions = 1

        return result, conversions, traderDataEncoded
    
    @staticmethod
    def weights(lamb, window):
        weights_raw = np.power(lamb, np.arange(window)[::-1])
        weights_norm = weights_raw/np.sum(weights_raw)
        return weights_norm