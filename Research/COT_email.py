import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as grdspec
import tradingWithPython as twp
import pandas as pd
import io
import os
from datetime import datetime
import quandl
quandl.ApiConfig.api_key = 'wxychbrgu7o7x3MRq4Hx'

def rank(array):
    # wrapper for pd.Series.rank function
    s = pd.Series(array)
    return s.rank()[len(s)-1]

def cotFunction1(sym):
    
    # create mapping table to Quandl symbols: continuous futures price, COT report, and COT Legacy report
    commodity = ['silver','gold','copper','crude','natgas','platinum', 'cotton','gasoline']
    symbols = [
        ['CHRIS/CME_SI1','CFTC/SI_FO_ALL','CFTC/SI_FO_L_ALL'],
        ['CHRIS/CME_GC1','CFTC/GC_FO_ALL','CFTC/GC_FO_L_ALL'],
        ['CHRIS/CME_HG1','CFTC/HG_FO_ALL','CFTC/HG_FO_L_ALL'],
        ['CHRIS/CME_CL1','CFTC/CL_FO_ALL','CFTC/CL_FO_L_ALL'],
        ['CHRIS/CME_NG1','CFTC/NG_FO_ALL','CFTC/NG_FO_L_ALL'],
        ['CHRIS/CME_PL1','CFTC/PL_FO_ALL','CFTC/PL_FO_L_ALL'],
        ['CHRIS/ICE_CT1','CFTC/CT_FO_ALL','CFTC/CT_FO_L_ALL'],
        ['CHRIS/CME_RB1','CFTC/RB_FO_ALL','CFTC/RB_FO_L_ALL']
    ]

    mapping = dict(list(zip(commodity,symbols)))

    symbol = mapping[sym]

    print ('retrieving price data')
    try:
        priceData = quandl.get(symbol[0])
    except Exception as e:
        print (e)
    print ('retrieving COT data')
    try:
        cotData = quandl.get(symbol[1])
    except Exception as e:
        print (e)
    print ('retrieving COT legacy data')
    try:
        cotLegacy = quandl.get(symbol[2])
    except Exception as e:
        print (e)

    # rename Producer columns
    for i, header in enumerate(list(cotData)):
        if list(cotData)[i].startswith('Producer') & list(cotData)[i].endswith('Longs'):
            cotData = cotData.rename(columns={
                list(cotData)[i]:'Producer Longs'
            })
        elif list(cotData)[i].startswith('Producer') & list(cotData)[i].endswith('Shorts'):
            cotData = cotData.rename(columns={
                list(cotData)[i]:'Producer Shorts'
            })

    # Merge COT data table and Settle Price
    price = priceData[['Settle']]
    price = price.fillna(method = 'ffill')
    cotData = cotData.merge(price, how='left', left_index=True, right_index=True)
    cotLegacy = cotLegacy.merge(price, how='left', left_index=True, right_index=True)

    # create new columns of rolling data
    roll_period = 260

    cotData['MMNet'] = (cotData['Money Manager Longs']-cotData['Money Manager Shorts'])
    cotData['MMNetOI'] = (cotData['Money Manager Longs']-cotData['Money Manager Shorts']) / cotData['Open Interest']
    # 5-year (260 weeks) rolling percentile (adjusted by open interest)
    cotData['MMNetOIPrctile'] = (cotData['MMNetOI'].rolling(window=roll_period).apply(rank)) / roll_period

    cotData['ProdNet'] = (cotData['Producer Longs']-cotData['Producer Shorts'])
    cotData['ProdNetOI'] = (cotData['Producer Longs']-cotData['Producer Shorts']) / cotData['Open Interest']
    cotData['ProdNetOIPrctile'] = (cotData['ProdNetOI'].rolling(window=roll_period).apply(rank)) / roll_period

    cotLegacy['CommNet'] = (cotLegacy['Commercial Long']-cotLegacy['Commercial Short'])
    cotLegacy['CommNetOI'] = (cotLegacy['Commercial Long']-cotLegacy['Commercial Short']) / cotData['Open Interest']
    cotLegacy['CommNetOIPrctile'] = (cotLegacy['CommNetOI'].rolling(window=roll_period).apply(rank)) / roll_period

    displayTable = cotData[['Open Interest','MMNet','MMNetOI','ProdNet','ProdNetOI','Settle']]

    s1 = cotData['Settle'].tail(len(cotData) - roll_period)
    s2 = cotData['MMNetOIPrctile'].tail(len(cotData) - roll_period)
    s3 = cotData['ProdNetOIPrctile'].tail(len(cotData) - roll_period)
    s4 = cotLegacy['CommNetOIPrctile'].tail(len(cotData) - roll_period)  # note: use length of cotData, not cotLegacy
    s5 = cotData['Open Interest'].tail(len(cotData) - roll_period)

    fig = plt.figure(figsize=(10, 6)) 
    gs = grdspec.GridSpec(3, 1, height_ratios=[3.5, 1.9, 1.9])  # 3 rows, 1 column
    ax0 = plt.subplot(gs[0])
    ax0.plot(s1)
    ax0.legend(loc='upper left')
    ax0.set_ylabel('Price')
    ax0.grid()
    ax1 = plt.subplot(gs[1])
    ax1.plot(s2, label='Money Manager %tile', color='g')
    ax1.plot(s3, label='Producer %tile', color='y')
    ax1.legend(loc='upper left')
    ax1.grid()
    ax2 = plt.subplot(gs[2])
    ax2.plot(s4, label='Commercial Net %tile', color='b')
    ax2.legend(loc='upper left')
    ax2.grid()
    ax3 = ax0.twinx()
    ax3.plot(s5, label='Open Interest', color='c')
    ax3.set_ylabel('Open Interest', color='c')
    #plt.show()
    
    return displayTable, fig


mymail = twp.email.Bimail('COT Weekly Positioning ' +datetime.now().strftime('%Y/%m/%d'), ['bard.ckchan@gmail.com'])

tbl, cotFig = cotFunction1('gold')
cotFig.suptitle('Gold')
cotFig.savefig(os.path.abspath('pics\\COT_gold') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_gold.png"/>') 
mymail.addattach(['pics/COT_gold.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('silver')
cotFig.suptitle('Silver')
cotFig.savefig(os.path.abspath('pics\\COT_silver') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_silver.png"/>') 
mymail.addattach(['pics/COT_silver.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('platinum')
cotFig.suptitle('Platinum')
cotFig.savefig(os.path.abspath('pics\\COT_plat') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_plat.png"/>') 
mymail.addattach(['pics/COT_plat.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('copper')
cotFig.suptitle('Copper')
cotFig.savefig(os.path.abspath('pics\\COT_copper') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_copper.png"/>') 
mymail.addattach(['pics/COT_copper.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('crude')
cotFig.suptitle('WTI Crude Oil')
cotFig.savefig(os.path.abspath('pics\\COT_crude') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_crude.png"/>') 
mymail.addattach(['pics/COT_crude.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('natgas')
cotFig.suptitle('Natural Gas')
cotFig.savefig(os.path.abspath('pics\\COT_natgas') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_natgas.png"/>') 
mymail.addattach(['pics/COT_natgas.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('cotton')
cotFig.suptitle('Cotton')
cotFig.savefig(os.path.abspath('pics\\COT_cotton') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_cotton.png"/>') 
mymail.addattach(['pics/COT_cotton.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

tbl, cotFig = cotFunction1('gasoline')
cotFig.suptitle('Gasoline')
cotFig.savefig(os.path.abspath('pics\\COT_gasoline') + '.png', format = 'png')
mymail.htmladd('<img src="cid:pics/COT_gasoline.png"/>') 
mymail.addattach(['pics/COT_gasoline.png'])
mymail.htmladd(((tbl.tail(10)).to_html()))

mymail.send()
