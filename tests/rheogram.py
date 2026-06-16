import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

PATH = "data/Bely_obrazets_myagkiy_0_1_s.csv"
#PATH = "data/ispytanie_1.csv"
#PATH = "data/ispytanie_2.csv"
#PATH = "data/ispytanie_3.csv"
df = pd.read_csv(PATH)

# Обрезаем с максимума, сдвигаем время в ноль
idx_max = df['Value'].idxmax()
t_max = df.loc[idx_max, 'Minutes']
df = df.loc[idx_max:].reset_index(drop=True)
df['Minutes'] = df['Minutes'] - t_max

WINDOW = 10 # ширина окна скользящего среднего (подбери под частоту сигнала)

df['rolling_mean'] = df['Value'].rolling(window=WINDOW, center=True, min_periods=1).mean()

fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(df['Minutes'], df['Value'], linewidth=0.7, color='steelblue', label='Сигнал')
ax.plot(df['Minutes'], df['rolling_mean'], color='red', linewidth=1.5,
        label=f'Скользящее среднее (окно={WINDOW})')

ax.set_xlabel('Время (мин от максимума)')
ax.set_ylabel('Value')
ax.set_title('Реограмма')
ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('rheogram.png', dpi=150)
plt.show()
