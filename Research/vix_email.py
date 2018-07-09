import matplotlib
matplotlib.use('Agg')
from matplotlib import pylab, mlab, pyplot
from IPython.core.pylabtools import figsize, getfigs
plt = pyplot

import io
import os
import tradingWithPython as twp
from tradingWithPython import sharpe # general trading toolbox functions
from tradingWithPython import cboe_ckc as ckc
import pandas as pd # pandas time series library
from datetime import datetime
import quandl
quandl.ApiConfig.api_key = 'wxychbrgu7o7x3MRq4Hx'

# read CSV from local drive
path1 = r'C:\Users\chekitsch\Documents\Trading\Historical data\VIX\vix_etf.csv'
etf = pd.read_csv(path1, index_col=0, header = 0, parse_dates=True)

path2 = r'C:\Users\chekitsch\Documents\Trading\Historical data\VIX\term_structure.csv'
vixfut = pd.read_csv(path2, index_col=0, header = 0, parse_dates=True)

# update SVXY and UVXY prices
try:
    existDate = etf.index[-1]
    sDate = existDate + pd.tseries.offsets.Day(weekday=1)   # shift forward existDate by 1 week day
    svxy = quandl.get('EOD/SVXY', start_date=sDate.date().isoformat())
    uvxy = quandl.get('EOD/UVXY', start_date=sDate.date().isoformat())

    if len(svxy) > 0:
        etfprice = [[]for i in range(3)]
        for i in range(len(svxy)):
            etfprice[0].append(svxy.index[i])
            etfprice[1].append(svxy.Adj_Close[i])
            etfprice[2].append(uvxy.Adj_Close[i])

        d = dict(list(zip(list(etf), etfprice[1:])))
        df = pd.DataFrame(d, index = pd.Index(etfprice[0]))
        etf = etf.append(df)
        etf.to_csv(path1)
except Exception as e:
    print (e)
	
# update VIX futures prices
vixfut = ckc.updateVixData(path2, vixfut)

# conform vixfut to etf.index
vixfut = vixfut.reindex(etf.index)

# merge etf with vixfut
vixfut = vixfut.merge(etf, how='left', left_index=True, right_index=True)

# calculate contango using front month contracts
vixfut['Contango1'] = (vixfut['UX1'] / vixfut['VIX'])-1
vixfut['Contango2'] = (vixfut['UX2'] / vixfut['UX1'])-1
vixfut['ContangoAvg'] = (vixfut['Contango1'] + vixfut['Contango2'])/2

# calculate 30 day VIX
vixfut['expiry'] = 0
vixfut['VIX_30day'] = 0
for i, d in enumerate(vixfut.index):
    vixfut.loc[vixfut.index[i],'expiry'] = ckc.vixExpiration(d.year, d.month)
    v1 = (vixfut.expiry[i] - vixfut.index[i]).days * vixfut.UX1[i]
    v2 = (30 - (vixfut.expiry[i] - vixfut.index[i]).days) * vixfut.UX2[i]
    vixfut.loc[vixfut.index[i],'VIX_30day'] = (1/30) * (v1 + v2)

# VIX 250-day moving average
vixfut['vix250ma'] = vixfut['VIX'].rolling(window=250).mean()
vixfut['vix250stdev'] = vixfut['VIX'].rolling(window=250).std()
vixfut['z_score'] = (vixfut['VIX'] - vixfut['vix250ma']) / vixfut['vix250stdev']

lookback = -300
figsize(8,3)
vixfut[['VIX','VIX_30day','vix250ma']][lookback:].plot(grid=True)
plt.savefig(os.path.abspath('pics\\vix_chart') + '.png', format = 'png')
vixfut[['ContangoAvg','z_score']][lookback:].plot(subplots=True,grid=True)
plt.savefig(os.path.abspath('pics\\vix_contango') + '.png', format = 'png')

#print (vixfut[['VIX','VIX_30day','vix250ma','vix250stdev','z_score','ContangoAvg']][-10:])

days_ago = [-1,-2,-5,-20]

plt.figure()
for i, d in enumerate(days_ago):
    vixfut.iloc[d,:9].plot(legend=True, grid=True)
plt.savefig(os.path.abspath('pics\\vix_ts') + '.png', format = 'png')


mymail = twp.email.Bimail('VIX analytics ' +datetime.now().strftime('%Y/%m/%d'), ['bard.ckchan@gmail.com', 'windflower17@hotmail.com'])
mymail.htmladd('Good morning, find the daily summary below.')
mymail.htmladd('VIX statistics')
mymail.htmladd(((vixfut[['VIX','VIX_30day','vix250ma','vix250stdev','z_score','ContangoAvg','SVXY','UVXY']][-10:]).to_html()))
mymail.htmladd('<img src="cid:pics/vix_chart.png"/>') 
mymail.addattach(['pics/vix_chart.png'])
mymail.htmladd('<img src="cid:pics/vix_contango.png"/>') 
mymail.addattach(['pics/vix_contango.png'])
mymail.htmladd('<img src="cid:pics/vix_ts.png"/>') 
mymail.addattach(['pics/vix_ts.png'])

mymail.send()
