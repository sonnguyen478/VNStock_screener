#import relevant libraries
import yfinance as yf
from datetime import datetime
from datetime import timedelta
import pandas as pd
from pandas_datareader import data as pdr
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
from mplfinance.original_flavor import candlestick_ohlc
import statistics
import yfinance as yf


def plot_Resistance_line(df, stock, start, log_scale=True, use_input_df=False, plot_show=True):
    
    GLV_lst = []
    try:
        if use_input_df==True:
            df = df[df.index >= start.strftime('%Y-%m-%d')]
        else:
            df = pdr.get_data_yahoo(stock, start, datetime.now()) #Fetches stock price data, saves as data frame
    except Exception:
        df = df[df.index >= start.strftime('%Y-%m-%d')]


    df.drop(df[df["Volume"]<1000].index, inplace=True)
    n_days = 10
    Range = np.zeros(2*n_days).tolist()
    dateRange = np.zeros(2*n_days).tolist()
    pivots = []
    dates = []
    count = 0
    
    for i in df.index:
        currMax = max(Range, default=0)
        value = df['High'][i]
        Range = Range[-2*n_days+1:]
        Range.append(value)
        dateRange = dateRange[-2*n_days+1:]
        dateRange.append(i)
        
        if currMax == max(Range, default = 0):
            count += 1
        else:
            count = 0
        if count ==n_days:
            pivots.append(currMax)
            dates.append(dateRange[Range.index(currMax)])

    # ===========================
    # print price chart
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    df['High'].plot(ax=ax1)
    ax1.set_ylabel('price in $')
    if log_scale==True:
        ax1.set_yscale('log')
    delta = 20
    for d,_ in enumerate(pivots):
#         ax1.hlines(pivots[d], xmin=dates[d]+timedelta(-90), xmax=dates[d]+timedelta(90), linestyle='--', color='green')
        plt.plot_date([dates[d]+timedelta(-delta),dates[d]+timedelta(delta)],
                      [pivots[d], pivots[d]], linestyle='--', color='green', marker=','
                     )
        plt.annotate(str(round(pivots[d],2)), (mdates.date2num(dates[d]), pivots[d]), xytext=(-10, 7), 
                textcoords='offset points',fontsize=9, arrowprops=dict(arrowstyle='-|>'))

    plt.legend(loc=0)
    plt.gcf().set_size_inches(18, 8)
    if plot_show:
        plt.show()

    return fig


def plot_OHLC_candle(df, stock, start, log_scale=True, use_input_df=False, plot_show=True):
    try:
        if use_input_df==True:
            prices = df[df.index >= start.strftime('%Y-%m-%d')]
        else:
            prices = pdr.get_data_yahoo(stock, start, datetime.now()) #Fetches stock price data, saves as data frame
    except Exception:
        prices = df[df.index >= start.strftime('%Y-%m-%d')]


    fig, ax1 = plt.subplots() #Create Plots

    #Calculate moving averages
    smasUsed=[10,30,50] #Choose smas
    for sma in smasUsed: #This for loop calculates the SMAs for the stated periods and appends to dataframe
        prices.loc[:,'SMA_'+str(sma)] = prices['Close'].rolling(window=sma).mean() #calcaulates sma and creates col

    #calculate Bollinger Bands
    BBperiod=15 #choose moving avera
    stdev=2
    prices.loc[:,'SMA'+str(BBperiod)] = prices['Close'].rolling(window=BBperiod).mean() #calculates sma and creates a column in the dataframe
    prices.loc[:,'STDEV']=prices['Close'].rolling(window=BBperiod).std() #calculates standard deviation and creates col
    prices.loc[:,'LowerBand']= prices['SMA'+str(BBperiod)]-(stdev*prices['STDEV']) #calculates lower bollinger band
    prices['LowerBand'] = prices['LowerBand'].apply(lambda x: 0 if x <0 else x)
    prices.loc[:,'UpperBand']=prices['SMA'+str(BBperiod)]+(stdev*prices['STDEV']) #calculates upper band
    prices.loc[:,"Date"]=mdates.date2num(prices.index) #creates a date column stored in number format (for OHCL bars)



    #Calculate 10.4.4 stochastic
    Period=10 #Choose stoch period
    K=4 # Choose K parameter
    D=4 # choose D parameter
    prices.loc[:,"RolHigh"] = prices["High"].rolling(window=Period).max() #Finds high of period
    prices.loc[:,"RolLow"] = prices["Low"].rolling(window=Period).min() #finds low of period
    prices.loc[:,"stok"] = ((prices["Close"]-prices["RolLow"])/(prices["RolHigh"]-prices["RolLow"]))*100 #Finds 10.1 stoch
    prices.loc[:,"K"] = prices["stok"].rolling(window=K).mean() #Finds 10.4 stoch
    prices.loc[:,"D"] = prices["K"].rolling(window=D).mean() #Finds 10.4.4 stoch
    prices.loc[:,"GD"]=prices["High"] #Create GD column to store green dots
    ohlc = [] #Create OHLC array which will store price data for the candlestick chart

    #Delete extra dates
#     if max(smasUsed) < prices.shape[0]:
#         prices=prices.iloc[max(smasUsed):]


    greenDotDate=[] #Stores dates of Green Dots
    greenDot=[] #Stores Values of Green Dots
    lastK=0 # Will store yesterday's fast stoch
    lastD=0 #will store yseterdays slow stoch
    lastLow=0 #will store yesterdays lower
    lastClose=0 #will store yesterdays close
    lastLowBB=0 # will store yesterdats lower bband


    #Go through price history to create candlestics and GD+Blue dots
    for i in prices.index: 
        #append OHLC prices to make the candlestick
        append_me = prices["Date"][i], prices["Open"][i], prices["High"][i], prices["Low"][i], prices["Close"][i], prices["Volume"][i]
        ohlc.append(append_me)

        #Check for Green Dot
        if prices['K'][i]>prices['D'][i] and lastK<lastD and lastK <60:

            #plt.Circle((prices["Date"][i],prices["High"][i]),1) 
            #plt.bar(prices["Date"][i],1,1.1,bottom=prices["High"][i]*1.01,color='g')
            plt.plot(prices["Date"][i],prices["High"][i]+1, marker="o", ms=6, ls="", color='orange') #plot green dot

            greenDotDate.append(i) #store green dot date
            greenDot.append(prices["High"][i])  #store green dot value

        #Check for Lower Bollinger Band Bounce
        if ((lastLow<lastLowBB) or (prices['Low'][i]<prices['LowerBand'][i])) and (prices['Close'][i]>lastClose and prices['Close'][i]>prices['LowerBand'][i]) and lastK <60:  
            plt.plot(prices["Date"][i],prices["Low"][i]-1, marker="o", ms=6, ls="", color='b') #plot blue dot

        #store values
        lastK=prices['K'][i]
        lastD=prices['D'][i]
        lastLow=prices['Low'][i]
        lastClose=prices['Close'][i]
        lastLowBB=prices['LowerBand'][i]


    #Plot moving averages and BBands
    for x in smasUsed: #This for loop calculates the EMAs for te stated periods and appends to dataframe
        sma=x
        prices['SMA_'+str(sma)].plot(label='close') 
    prices['UpperBand'].plot(label='close', color='lightgray') 
    prices['LowerBand'].plot(label='close', color='lightgray') 

    #plot candlesticks
    candlestick_ohlc(ax1, ohlc, width=.5, colorup='green', colordown='r', alpha=0.75)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) #change x axis back to datestamps
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(prices.shape[0]//5)) #add more x axis labels
    plt.tick_params(axis='x', rotation=45) #rotate dates for readability

    #Pivot Points
    pivots=[] #Stores pivot values
    dates=[]  #Stores Dates corresponding to those pivot values
    counter=0 #Will keep track of whether a certain value is a pivot
    lastPivot=0 #Will store the last Pivot value

    Range=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0] #Array used to iterate through stock prices
    dateRange=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0] #Array used to iterate through corresponding dates
    for i in prices.index: #Iterates through the price history
        currentMax=max(Range, default=0) #Determines the maximum value of the 10 item array, identifying a potential pivot
        value=round(prices["High"][i],2) #Receives next high value from the dataframe

        Range=Range[1:9] # Cuts Range array to only the most recent 9 values
        Range.append(value) #Adds newest high value to the array
        dateRange=dateRange[1:9]  #Cuts Date array to only the most recent 9 values
        dateRange.append(i) #Adds newest date to the array

        if currentMax == max(Range, default=0): #If statement that checks is the max stays the same
            counter+=1 #if yes add 1 to counter
        else:
            counter=0 #Otherwise new potential pivot so reset the counter
        if counter==5: # checks if we have identified a pivot
            lastPivot=currentMax #assigns last pivot to the current max value
            dateloc=Range.index(lastPivot) #finds index of the Range array that is that pivot value
            lastDate=dateRange[dateloc] #Gets date corresponding to that index
            pivots.append(currentMax) #Adds pivot to pivot array
            dates.append(lastDate) #Adds pivot date to date array
    print()

    timeD=timedelta(days=30) #Sets length of dotted line on chart

    for index in range(len(pivots)) : #Iterates through pivot array

        #print(str(pivots[index])+": "+str(dates[index])) #Prints Pivot, Date couple
        plt.plot_date([dates[index]-(timeD*.075), dates[index]+(timeD*.075)], #Plots horizontal line at pivot value
                    [pivots[index], pivots[index]], linestyle="--", linewidth=1, marker=',', color='green')
        plt.annotate(str(int(pivots[index])), (mdates.date2num(dates[index]), pivots[index]), xytext=(-10, 7), 
                textcoords='offset points',fontsize=9, arrowprops=dict(arrowstyle='-|>'))

    plt.xlabel('Date') #set x axis label
    plt.ylabel('Price') #set y axis label
    plt.title(stock+" - Daily") #set title
    plt.ylim(prices["Low"].min(), prices["High"].max()*1.05) #add margins
    if log_scale == True:
        plt.yscale("log")

    plt.gcf().set_size_inches(18, 8)
    if plot_show:
        plt.show()

    return fig


def plot_SMA_change_percentile(df, stock, start, log_scale=True, use_input_df=False, sma=50, limit=10, plot_show=True):
    try:
        if use_input_df==True:
            df = df[df.index >= start.strftime('%Y-%m-%d')]
        else:
            df = pdr.get_data_yahoo(stock, start, datetime.now()) #Fetches stock price data, saves as data frame
    except Exception:
        df = df[df.index >= start.strftime('%Y-%m-%d')]
    
#     sma = int(input("Enter the sma : ")) #Asks for stock ticker
#     limit= int(input("Enter Warning Limit : "))
    df.loc[:,'SMA'+str(sma)] = df["Close"].rolling(window=sma).mean() #calculates sma and creates a column in the dataframe
    df.loc[:,'PC'] = ((df["Close"]/df['SMA'+str(sma)])-1)*100

    mean =df["PC"].mean()
    stdev=df["PC"].std()
    current=df["PC"].iloc[-1]
    yday=df["PC"].iloc[-2]



    print(str(current))

    print("Mean: "+str(mean))
    print("Standard Dev: "+str(stdev))


    bins = np.arange(-100, 100, 1) # fixed bin size

#     fig = plt.figure()
#     ax = fig.add_subplot(221)
#     fig, ((ax, ax1), (ax2, ax3)) = plt.subplots(2, 2)    
#     plt.gcf().set_size_inches(18, 8)
    
    fig1, ax1 = plt.subplots()
    df['High'].plot(ax=ax1)
    ax1.set_ylabel('price in VND')
    if log_scale==True:
        ax1.set_yscale('log')
    plt.legend(loc=0)
    plt.gcf().set_size_inches(18, 8)

    
    fig2, ax2 = plt.subplots() #Create Plots
#     ax2 = fig.add_subplot(223)
#     df=df[-150:]
    df['PC'].plot(label='close',color='k')
    plt.title(stock+"-- % From "+str(sma)+" Over last 100 days")
    plt.xlabel('Date') 
    plt.ylabel('Percent from '+str(sma)+' EMA')
#     ax2.xaxis.set_major_locator(mticker.MaxNLocator(df.shape[0]//5)) #add more x axis labels
    plt.axhline( y=limit, xmin=0, xmax=1, color='r')
    plt.gcf().set_size_inches(18, 8)


    fig3, ax3 = plt.subplots() #Create Plots
#     ax1 = fig.add_subplot(222)
    plt.xlim([df["PC"].min()-5, df["PC"].max()+5])

    plt.hist(df["PC"], bins=bins, alpha=0.5)
    plt.title(stock+"-- % From "+str(sma)+" SMA Histogram since "+start.strftime('%Y-%m-%d'))
    plt.xlabel('Percent from '+str(sma)+' SMA (bin size = 1)')
    plt.ylabel('Count')

    plt.axvline( x=mean, ymin=0, ymax=1, color='k', linestyle='--')
    plt.axvline( x=stdev+mean, ymin=0, ymax=1, color='gray', alpha=1, linestyle='--')
    plt.axvline( x=2*stdev+mean, ymin=0, ymax=1, color='gray',alpha=.75, linestyle='--')
    plt.axvline( x=3*stdev+mean, ymin=0, ymax=1, color='gray', alpha=.5, linestyle='--')
    plt.axvline( x=-stdev+mean, ymin=0, ymax=1, color='gray', alpha=1, linestyle='--')
    plt.axvline( x=-2*stdev+mean, ymin=0, ymax=1, color='gray',alpha=.75, linestyle='--')
    plt.axvline( x=-3*stdev+mean, ymin=0, ymax=1, color='gray', alpha=.5, linestyle='--')

    plt.axvline( x=current, ymin=0, ymax=1, color='r')
    plt.axvline( x=yday, ymin=0, ymax=1, color='blue')

    ax3.xaxis.set_major_locator(mticker.MaxNLocator(21)) #add more x axis labels
    plt.gcf().set_size_inches(18, 8)

    if plot_show:
        plt.show()

    return fig1, fig2, fig3


def compute_BB_Stoch(df, BBperiod=15, stdev=2, Period=10, K=4, D=4):
    #calculate Bollinger Bands
    df.loc[:,'SMA'+str(BBperiod)] = df['Close'].rolling(window=BBperiod).mean() #calculates sma and creates a column in the dataframe
    df.loc[:,'STDEV']=df['Close'].rolling(window=BBperiod).std() #calculates standard deviation and creates col
    df.loc[:,'LowerBand']= df['SMA'+str(BBperiod)]-(stdev*df['STDEV']) #calculates lower bollinger band
    df['LowerBand'] = df['LowerBand'].apply(lambda x: 0 if x <0 else x)
    df.loc[:,'UpperBand']=df['SMA'+str(BBperiod)]+(stdev*df['STDEV']) #calculates upper band

    #Calculate 10.4.4 stochastic
    df.loc[:,"RolHigh"] = df["High"].rolling(window=Period).max() #Finds high of period
    df.loc[:,"RolLow"] = df["Low"].rolling(window=Period).min() #finds low of period
    df.loc[:,"stok"] = ((df["Close"]-df["RolLow"])/(df["RolHigh"]-df["RolLow"]))*100 #Finds 10.1 stoch
    df.loc[:,"K"] = df["stok"].rolling(window=K).mean() #Finds 10.4 stoch
    df.loc[:,"D"] = df["K"].rolling(window=D).mean() #Finds 10.4.4 stoch
    df.loc[:,"GD"]= 0
    df.loc[:,"BD"]= 0

    greenDotDate=[] #Stores dates of Green Dots
    greenDot=[] #Stores Values of Green Dots
    lastK=0 # Will store yesterday's fast stoch
    lastD=0 #will store yseterdays slow stoch
    lastLow=0 #will store yesterdays lower
    lastClose=0 #will store yesterdays close
    lastLowBB=0 # will store yesterdats lower bband
    for i in df.index: 
        #Check for Green Dot
        if df['K'][i]>df['D'][i] and lastK<lastD and lastK <60:
            df.at[i, 'GD'] = 1
        #Check for Lower Bollinger Band Bounce
        if ((lastLow<lastLowBB) or (df['Low'][i]<df['LowerBand'][i])) and \
        (df['Close'][i]>lastClose and df['Close'][i]>df['LowerBand'][i]) and lastK <60:  
            df.at[i, 'BD'] = 1

        #store values
        lastK=df['K'][i]
        lastD=df['D'][i]
        lastLow=df['Low'][i]
        lastClose=df['Close'][i]
        lastLowBB=df['LowerBand'][i]

    
    return df


def SMA(input_pd, day):
    input_pd.loc[:,"SMA_"+str(day)]=round(input_pd["Close"].rolling(window=day).mean(),2)
    return input_pd


def Bollinger_Band(input_pd, BBperiod=15, stdev=2):
    """
    Compute Bollinger Band for stock Closed price time series
    Input:
    + input_pd: input Pandas DataFrame
    + BBperiod: compute on period (days, default=15)
    + stdev: standard deviation coef (days, default=2)
    """

    input_pd.loc[:,'SMA'+str(BBperiod)] = input_pd['Close'].rolling(window=BBperiod).mean() #calculates sma and creates a column in the dataframe
    input_pd.loc[:,'STDEV']=input_pd['Close'].rolling(window=BBperiod).std() #calculates standard deviation and creates col
    input_pd.loc[:,'LowerBand']= input_pd['SMA'+str(BBperiod)]-(stdev*input_pd['STDEV']) #calculates lower bollinger band
    input_pd['LowerBand'] = input_pd['LowerBand'].apply(lambda x: 0 if x <0 else x)
    input_pd.loc[:,'UpperBand']=input_pd['SMA'+str(BBperiod)]+(stdev*input_pd['STDEV']) #calculates upper band

    return input_pd


def Stochastic(input_pd, Period=10, K=4, D=4):
    """
    Compute Bollinger Band for stock Closed price time series
    Input:
    + input_pd: input Pandas DataFrame
    + Period: compute on period (days, default=10)
    + K: K coef (days, default=4)
    + D: D coef (days, default=4)
    """

    input_pd.loc[:,"RolHigh"] = input_pd["High"].rolling(window=Period).max() #Finds high of period
    input_pd.loc[:,"RolLow"] = input_pd["Low"].rolling(window=Period).min() #finds low of period
    input_pd.loc[:,"stok"] = ((input_pd["Close"]-input_pd["RolLow"])/(input_pd["RolHigh"]-input_pd["RolLow"]))*100 #Finds 10.1 stoch
    input_pd.loc[:,"K"] = input_pd["stok"].rolling(window=K).mean() #Finds 10.4 stoch
    input_pd.loc[:,"D"] = input_pd["K"].rolling(window=D).mean() #Finds 10.4.4 stoch
    input_pd.loc[:,"GD"]= 0
    input_pd.loc[:,"BD"]= 0

    return input_pd