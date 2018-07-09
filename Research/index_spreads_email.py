import matplotlib
matplotlib.use('Agg')
from matplotlib import pylab, mlab, pyplot
from IPython.core.pylabtools import figsize, getfigs
plt = pyplot

import io
import os
import tradingWithPython as twp
from tradingWithPython import sharpe # general trading toolbox functions
import pandas as pd # pandas time series library
from datetime import datetime
import quandl
quandl.ApiConfig.api_key = 'wxychbrgu7o7x3MRq4Hx'



def backtest(ret_nday, ret_1d, window=15, ma_thresh = 0.6, ma_window=50, z_enter=2.5, z_enter2=0, z_exit=1.75):
    """
    Parameters
    ret_nday: n-day rolling returns (designed to catch big but gradual deviation from mean)
    ret_1d: 1-day return used to calculate synthetic price
    window: used to calculate z-score (entry signal) on n-day rolling returns
    ma_thresh: additional entry signal to complement z-score; difference between synth. price and its moving avg
    z_enter: threshold to initiate position
    z_enter2: default = 0 (i.e. off), add to initial position
    z_exit: target level (exit signal) used to close position
    
    """
    
    price = 100 * ret_1d.cumsum()  # synthetic price
        
    #----indicators
    z_score = ret_nday / ret_nday.rolling(window=window).std()  # current day z-score
    aboveAverage = (price - price.rolling(window=ma_window).mean()) > ma_thresh # is the price above average by 0.5? T/F, window size fixed
    belowAverage = (price - price.rolling(window=ma_window).mean()) < -ma_thresh # is the price below average by 0.5? T/F, window size fixed

    """ backtest with entering on a given z_score """
    pos = pd.Series(index = ret_nday.index, data = 0)  # position vector

    pos[(aboveAverage & (z_score > z_enter))] = -1 # short position
    pos[(belowAverage & (z_score < -z_enter))] = 1 # long position
    if z_enter2:                                    # double down if z-score hits 2nd z-entry
        pos[(aboveAverage & (z_score > z_enter2))] = -2 # short position
        pos[(belowAverage & (z_score < -z_enter2))] = 2 # long position
        
    for i,p in enumerate(pos):
        if i > 0 and pos[i-1] > 0 and z_score[i] < z_exit:  # if long, and z_score has not hit target, hold
            pos[i] = pos[i-1]
        elif i > 0 and pos[i-1] < 0 and z_score[i] > -z_exit:  # if short position and z_score has not hit target, keep shorting
            pos[i] = pos[i-1]

    #print (pos.value_counts())
    pos = pos.shift(1) # todays position has effect on tomorrows return. Shift 1 day into future.
    pnl = ret_1d*pos # daily pnl 
    return pd.DataFrame({'pnl':pnl,'pos':pos})




# read CSV from local drive
path1 = r'C:\Users\chekitsch\Documents\Trading\Historical data\JP\NTpair.csv'
NTpair = pd.read_csv(path1, index_col=0, header = 0, parse_dates=True)

existDate = NTpair.index[-1]

try:
    url = 'http://stocks.finance.yahoo.co.jp/stocks/history/?code=998407.O'
    tbl = pd.read_html(url, index_col = 0, header=0, parse_dates=True)
    df1 = tbl[1].set_index(pd.to_datetime(tbl[1].index, format='%Y年%m月%d日'))

    url = 'http://stocks.finance.yahoo.co.jp/stocks/history/?code=998405.T'
    tbl = pd.read_html(url, index_col = 0, header=0, parse_dates=True)
    df2 = tbl[1].set_index(pd.to_datetime(tbl[1].index, format='%Y年%m月%d日'))
except Exception as e:
    print (e)

nky_new = df1[df1.index > existDate].iloc[:,3].sort_index()
tpx_new = df2[df2.index > existDate].iloc[:,3].sort_index()

if len(nky_new) and len(tpx_new):
    print ('Existing Date: {0}   updating to nky_new.index(-1)'.format(existDate.date()))
    df_new = pd.DataFrame({'nky':nky_new, 'tpx': tpx_new})
    NTpair = NTpair.append(df_new)
    NTpair.to_csv(path1)
    print ('Update successful')
else:
    print ('Up to date as of ', existDate.date())


NTpair['spread_pct'] = NTpair.nky.pct_change() - NTpair.tpx.pct_change()
delta = 10   # x-day return
NTpair['spread_pct_N'] = NTpair.nky.pct_change(delta) - NTpair.tpx.pct_change(delta)
NTpair['spread'] = NTpair.nky*8 - NTpair.tpx*100  # spread scaled according to futures multiplier
NTpair['spread_ratio'] = NTpair.nky / NTpair.tpx

R = NTpair['spread_pct'].dropna()
R_nday = NTpair['spread_pct_N'].dropna()

indicators = pd.DataFrame(index = R.index) #prepare indicators DataFrame

indicators['spread'] = NTpair['spread']
indicators['spread_ratio'] = NTpair['spread_ratio']
indicators['z_score'] = R_nday/R_nday.rolling(window=25).std() # current day return z-score
indicators['cumRet'] = 100 * R.cumsum() # total sum of returns, which is a sythetic price
indicators['ma'] = indicators['cumRet'].rolling(window=200).mean() #moving average of synthetic price
indicators['momentum'] = indicators['cumRet']-indicators['ma'] # difference between synth. 
                                                                #price and ma, gives indication of momentum strength
#print (indicators.tail(5))

figsize(8,3)
indicators[['cumRet','ma']].tail(750).plot(grid=True, title='Nikkei-TOPIX spread')
plt.savefig(os.path.abspath('pics\\NT_spread') + '.png', format = 'png')
plt.figure()
indicators[['z_score','momentum']].tail(750).plot(grid=True)
plt.savefig(os.path.abspath('pics\\NT_zscore') + '.png', format = 'png')

# strategy parameters
win, ma_win, z_enter, z_enter2, z_exit = 25, 200, 2.5, 3.75, 1.9
NTdf = backtest(NTpair['spread_pct_N'], NTpair['spread_pct'], window=win, ma_thresh = 0.5, ma_window=ma_win, z_enter=z_enter, z_enter2=z_enter2, z_exit=z_exit)

period = 750
plt.figure()
NTdf.pos.tail(period).plot(title='Position')
plt.savefig(os.path.abspath('pics\\NT_position') + '.png', format = 'png')
plt.figure()
NTdf.pnl.tail(period).cumsum().plot(grid=True, title='P&L')
plt.savefig(os.path.abspath('pics\\NT_pnl') + '.png', format = 'png')
#print ('Sharpe since 2000: ', twp.sharpe(NTdf.pnl))
#print ('Sharpe trailing {0} days: {1}'.format(period, twp.sharpe(NTdf.pnl.tail(750))) )
#print ('{0}-day P&L: '.format(NTdf.pnl.tail(period).cumsum()[-1]))


mymail = twp.email.Bimail('Nikkei-Topix spread ' +datetime.now().strftime('%Y/%m/%d'), ['bard.ckchan@gmail.com', 'windflower17@hotmail.com'])
mymail.htmladd(((indicators.tail(10)).to_html()))
mymail.htmladd('<img src="cid:pics/NT_spread.png"/>') 
mymail.addattach(['pics/NT_spread.png'])
mymail.htmladd('<img src="cid:pics/NT_zscore.png"/>') 
mymail.addattach(['pics/NT_zscore.png'])
mymail.htmladd('window = {0} | ma_window = {1} | z-enter = {2} | z-enter2 = {3} | z-exit = {4}'.format(win, ma_win, z_enter, z_enter2, z_exit))
mymail.htmladd('<img src="cid:pics/NT_position.png"/>') 
mymail.addattach(['pics/NT_position.png'])
mymail.htmladd('<img src="cid:pics/NT_pnl.png"/>') 
mymail.addattach(['pics/NT_pnl.png'])
mymail.htmladd(('Sharpe since 2000: ' + str(twp.sharpe(NTdf.pnl))))
mymail.htmladd('Sharpe trailing {0} days: {1}'.format(period, twp.sharpe(NTdf.pnl.tail(750))))
mymail.htmladd('{0}-day P&L: {1}'.format(period, NTdf.pnl.tail(period).cumsum()[-1]))

mymail.send()

