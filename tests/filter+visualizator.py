import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter

#0.8494979333333333,-364.64068603515625
sg_win = 300
SG_POLY = 4
#нужен опрос < 0.1 c. причем нужно фильтровать по максимуму
path = "Bely_obrazets_myagkiy_0_1_s.csv"
#path = "0_05_sek_oranzhevaya_rezina.csv"
#path = "chernaya_reina.csv"
#path = "Oranzhevy_obrazets_tverdy_0_1_s.csv"
#path = "0_01_sek.csv"
df = pd.read_csv(f'./data/{path}')
start_time = df.loc[df["Value"].idxmax(), 'Minutes']
df = df[df["Minutes"] >= start_time].reset_index(drop=True)
'''
# maximum rolling — center=True: пик попадает в центр окна, не обрезается
df['smoothed'] = df['Value'].rolling(window=6, center=True).max().bfill().ffill()
smoothed = savgol_filter(df['smoothed'].values,
                         window_length=sg_win,
                         polyorder=SG_POLY,
                         mode='nearest')
# не даём огибающей упасть ниже rolling max (защита от артефакта на краю)
df['smoothed_with_savgol'] = np.maximum(smoothed, df['smoothed'].values)
'''
df = df[df["Minutes"] >= start_time]
# maximum rolling
#df['smoothed'] = df['smoothed'].rolling(window=40).mean()
df['smoothed'] = df['Value'].rolling(window=20, min_periods=1).max()
df['smoothed_with_savgol'] = savgol_filter(df.smoothed, 
                                        window_length=sg_win,
                                        polyorder=SG_POLY,
                                        mode='nearest')
_ , axes = plt.subplots(2, 2)

# Верхний левый угол — линейный график
axes[0, 0].plot(df["Minutes"], df["Value"])
axes[0, 0].plot(df["Minutes"], df["smoothed"], color = "red")
axes[0, 0].set_title("Белая резина(мягкая) - простая с максимумами")

# Верхний правый угол — диаграмма рассеяния
axes[0, 1].plot(df["Minutes"], df["Value"])
axes[0, 1].plot(df["Minutes"], df["smoothed_with_savgol"], color = "red")
axes[0, 1].set_title("Умные максимумы")
'''
# Нижний левый угол — столбчатая диаграмма
axes[1, 0].plot(df["Minutes"], df["smoothed"])
axes[1, 0].plot(df["Minutes"], df["envelope"], color = "red")
axes[1, 0].set_title("Сравнение")

axes[1, 1].plot(df["Minutes"], df["maxed_value"])
axes[1, 1].set_title("Предоброботка")
'''
plt.legend()
plt.show()
