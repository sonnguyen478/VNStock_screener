import os
import json
import sys
import glob
import numpy as np
import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr
from datetime import datetime
from datetime import timedelta
from tqdm import tqdm
import importlib
import requests
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from pandas import ExcelWriter
from IPython.core.display import display, HTML

# import custom lib
from strat_configs import fconf
import strat_helpers
importlib.reload(strat_helpers)
from strat_helpers import *
import strat_utils
importlib.reload(strat_utils)
from strat_utils import *
pd.options.mode.chained_assignment = None


# Read zip files from page, download file, extract and stream output
from io import BytesIO
from zipfile import ZipFile
import urllib.request
import os,sys,requests,csv
from bs4 import BeautifulSoup

dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'CafeF/')

# check for download directory existence; create if not there
if not os.path.isdir(dir_path):
    os.makedirs(dir_path)

# Get labels and zip file download links
url = "https://s.cafef.vn/du-lieu/download.chn#data"

# get page and setup BeautifulSoup
r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")

#############################################################################
# lookup new date for download the data
# upto_date = '20210311'
today = (datetime.now().strftime('%Y%m%d') if datetime.now().strftime('%A') != "Saturday" and datetime.now().strftime('%A') != "Sunday" 
            else (datetime.now() + timedelta(days=(5-datetime.now().isoweekday()))).strftime('%Y%m%d'))    
# check data folder is empty
if len(list(glob.glob(os.path.join(dir_path, '*')))) == 0:
	input_date_lst = [today]
else:
	latest_date = (max([datetime.strptime(f.split('Upto')[1].split('.csv')[0].replace('.',''),"%d%m%Y") 
	     for f in os.listdir(dir_path) if 'CafeF.HSX.Upto' in f]))
	upto_date = ((latest_date + timedelta(days=1)) if latest_date.strftime('%A') != "Friday" 
	            else (latest_date + timedelta(days=(8-latest_date.isoweekday()))))
	upto_date = upto_date.strftime('%Y%m%d')
	input_date_lst = sorted(list(set([upto_date, today])))
print(input_date_lst)
do_logging(json.dumps(input_date_lst))
outputFilename=dir_path

keywords = ['Upto 3 sàn (điều chỉnh)', 'Upto 3 sàn (chưa điều chỉnh)', 'Upto Cung cầu & Khối ngoại']
for upto_date in input_date_lst:
    is_existed = False
    is_found = False
    for td in soup.find_all(lambda tag: tag.name=='li'):
        if any(x in td.get_text(strip=True) for x in keywords):
            link = td.find_next('a')
            if upto_date in link['href']:
                is_found = True
                do_logging(link['href'])
                # print(td.get_text(strip=True), link['href'] if link else '')

                # Downloading and streaming
                # Unzip and stream CSV file
                zipurl=link['href']
                zipname = link['href'].split('/')[-1]
                output_path = os.path.join(outputFilename,zipname)
                if os.path.exists(output_path):
                    is_existed = True
                    print('\tFile already existed')
                    do_logging('\tFile already existed')
                    continue

                # send notification to slack
                post_message_to_slack("Found new data {}".format(zipname))
                url = urllib.request.urlopen(zipurl)
                zippedData = url.read()

                # Save zip file to disk
                print ("\tSaving to ",output_path)
                do_logging('\tSaving to {}'.format(output_path))
                output = open(output_path,'wb')
                output.write(zippedData)
                output.close()

                # Extract file 
                print ("\tExtracting to ",outputFilename)
                do_logging('Extracting to {}'.format(outputFilename))
                with ZipFile(output_path, 'r') as zip_ref:
                    for contained_file in zip_ref.namelist():
                        if os.path.exists(os.path.join(outputFilename,contained_file)):
                            print("File exits",contained_file)
                            is_existed=True
                            break
                    if not is_existed:
                        post_message_to_slack("Extracting {}".format(zipname))
                        zip_ref.extractall(outputFilename)

    if is_existed or not is_found:
        post_message_to_slack("Stock data is upto date") 
        do_logging('Stock data is upto date')             
    else:
        # delete old data and keep only the latest date
        strat_helpers.delete_file_by_date(dir_path, datetime.strptime(upto_date,'%Y%m%d').strftime('%d.%m.%Y'))
        post_message_to_slack("Finish download and extract new data")
        do_logging('Finish download and extract new data') 

        #############################################################################
        # Load latest stock price
        HSX_latest_fname = 'CafeF.HSX.Upto{}.csv'.format(datetime.strptime(upto_date, "%Y%m%d").strftime("%d.%m.%Y"))
        HNX_latest_fname = 'CafeF.HNX.Upto{}.csv'.format(datetime.strptime(upto_date, "%Y%m%d").strftime("%d.%m.%Y"))
        UPCOM_latest_fname = 'CafeF.UPCOM.Upto{}.csv'.format(datetime.strptime(upto_date, "%Y%m%d").strftime("%d.%m.%Y"))
        print(HSX_latest_fname, HNX_latest_fname, UPCOM_latest_fname)

        def read_stock_file(fpath):
            pd_01 = pd.read_csv(fpath)
            pd_01.columns = ['Stock', 'Date','Open','High','Low','Close', 'Volume']
            pd_01.loc[:,'Date'] = pd.to_datetime(pd_01['Date'].astype(str),format= '%Y%m%d', errors='ignore')
            # pd_01.loc[:, 'RS Rating'] = 99
            pd_01['Open'] = (pd_01['Open']*1000).astype(int)
            pd_01['High'] = (pd_01['High']*1000).astype(int)
            pd_01['Close'] = (pd_01['Close']*1000).astype(int)
            pd_01['Low'] = (pd_01['Low']*1000).astype(int)

            return pd_01

        pd_01 = read_stock_file(os.path.join(dir_path, HSX_latest_fname))
        pd_02 = read_stock_file(os.path.join(dir_path, HNX_latest_fname))
        pd_03 = read_stock_file(os.path.join(dir_path, UPCOM_latest_fname))
        pd_01 = pd.concat([pd_01, pd_02, pd_03]).drop_duplicates()
        # stocklist = pd_01[['Stock','RS Rating']].drop_duplicates()
        stocklist = pd_01[['Stock']].drop_duplicates()
        print('Number of stock:', stocklist.shape[0])
        print(pd_01.shape)
        display(pd_01.head())
        do_logging('Number of stock: {}'.format(stocklist.shape[0]))
        do_logging(pd_01.shape)

        #############################################################################
        # check stock condition
        exportList= pd.DataFrame(columns=['Stock', "Curr Close", "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
        start =datetime(2017,12,1)
        for i in tqdm(stocklist.index):
            stock=str(stocklist["Stock"][i])
            # RS_Rating=90#stocklist["RS Rating"][i]

            try:
        #         df = pdr.get_data_yahoo(stock, start, datetime.now())
                df = pd_01.query('Stock == "{}"'.format(stock)).sort_values('Date')

                smaUsed=[50,150,200]
                for x in smaUsed:
                    sma=x
                    df["SMA_"+str(sma)]=round(df["Close"].rolling(window=sma).mean(),2)


                currentClose=df["Close"].iloc[-1]
                moving_average_50=df["SMA_50"].iloc[-1]
                moving_average_150=df["SMA_150"].iloc[-1]
                moving_average_200=df["SMA_200"].iloc[-1]
                low_of_52week=min(df["Close"][-260:])
                high_of_52week=max(df["Close"][-260:])
                try:
                    moving_average_200_20 = df["SMA_200"].iloc[-20]

                except Exception:
                    moving_average_200_20=0

                #Condition 1: Current Price > 150 SMA and > 200 SMA
                if(currentClose>moving_average_150>moving_average_200):
                    cond_1=True
                else:
                    cond_1=False
                #Condition 2: 150 SMA and > 200 SMA
                if(moving_average_150>moving_average_200):
                    cond_2=True
                else:
                    cond_2=False
                #Condition 3: 200 SMA trending up for at least 1 month (ideally 4-5 months)
                if(moving_average_200>moving_average_200_20):
                    cond_3=True
                else:
                    cond_3=False
                #Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
                if(moving_average_50>moving_average_150>moving_average_200):
                    #print("Condition 4 met")
                    cond_4=True
                else:
                    #print("Condition 4 not met")
                    cond_4=False
                #Condition 5: Current Price > 50 SMA
                if(currentClose>moving_average_50):
                    cond_5=True
                else:
                    cond_5=False
                #Condition 6: Current Price is at least 30% above 52 week low (Many of the best are up 100-300% before coming out of consolidation)
                if(currentClose>=(1.3*low_of_52week)):
                    cond_6=True
                else:
                    cond_6=False
                #Condition 7: Current Price is within 25% of 52 week high
                if(currentClose>=(.75*high_of_52week)):
                    cond_7=True
                else:
                    cond_7=False
                #Condition 8: IBD RS rating >70 and the higher the better
        #         if(RS_Rating>70):
        #             cond_8=True
        #         else:
        #             cond_8=False

                if(cond_1 and cond_2 and cond_3 and cond_4 and cond_5 and cond_6 and cond_7):# and cond_8):
                    exportList = exportList.append({'Stock': stock, "Curr Close": currentClose, "50 Day MA": moving_average_50, "150 Day Ma": moving_average_150, "200 Day MA": moving_average_200, "52 Week Low": low_of_52week, "52 week High": high_of_52week}, ignore_index=True)
            except Exception as e:
                print(e)
                print("No data on "+stock)
                do_logging("No data on {}".format(stock))

        output_path = os.path.join(outputFilename,'ScreenOutput_VNstock_{}.csv'.format(upto_date))
        print('WRITING into... {}'.format(output_path))
        exportList.to_csv(output_path, index=False)
        display(exportList)

        #############################################################################
        # send notification to slack
        post_message_to_slack('Your favorite stocks pass the condition')
        post_message_to_slack(exportList.query('Stock  in {}'.format(fconf['fav_lst'])).to_markdown())

        # send chart image to slack
        for stock in fconf['fav_lst']:
            print("*"*40)
            print("*"*18, stock, "*"*17)
            print("*"*40)
            df = pd_01.query('Stock == "{}"'.format(stock)).sort_values('Date').set_index('Date')
            del df['Stock']
            try:
                if stock == "MSB":
                    fig1, fig2, fig3 = plot_SMA_change_percentile(df, stock, datetime(2018,1,1),use_input_df=True, sma=10, plot_show=False)
                else:
                    fig1, fig2, fig3 = plot_SMA_change_percentile(df, stock, datetime(2018,1,1),use_input_df=True, plot_show=False)
                post_message_to_slack('*'*80)
                send_image_to_slack(fig2, fconf['slack_channel'], 'Percent from 50EMA over last 100days', stock)
                send_image_to_slack(fig3, fconf['slack_channel'], 'Histogram Percent from 50SMA')

                fig1 = plot_Resistance_line(df, stock, datetime(2018,1,1), log_scale=False,use_input_df=True, plot_show=False)
                send_image_to_slack(fig1, fconf['slack_channel'], 'Resistance line')
                fig1 = plot_OHLC_candle(df, stock, datetime(2020,1,1),use_input_df=True, plot_show=False)
                send_image_to_slack(fig1, fconf['slack_channel'], 'Candle chart', dpi=400)
            except:
                print('No data on ', stock)
                do_logging("No data on {}".format(stock))


