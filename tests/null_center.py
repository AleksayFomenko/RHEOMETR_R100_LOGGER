import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
# --- 1. Загрузка ---
INPUT = f'data/Bely_obrazets_myagkiy_0_1_s.csv'
INPUT = f'data/0_05_sek_oranzhevaya_rezina.csv'
df = pd.read_csv(INPUT)
print(f"Исходно строк: {len(df)}")

# --- 2. Обрезка: начинаем с максимума ---
idx_max = df['Value'].idxmax()
t_max = df.loc[idx_max, 'Minutes']
df_cut = df.loc[idx_max:].reset_index(drop=True)
# Сдвинем время, чтобы отсчёт начинался с 0 от точки максимума
df_cut['Minutes'] = df_cut['Minutes'] - t_max
print(f"Обрезано с индекса {idx_max} (t={t_max:.4f} мин), осталось строк: {len(df_cut)}")

# --- 3. Условный ноль = среднее по сигналу (устойчиво к одиночным выбросам) ---
v_min  = df_cut['Value'].min()
v_max  = df_cut['Value'].max()
v_mean = df_cut['Value'].mean()
mid    = v_mean
print(f"min={v_min:.3f}, max={v_max:.3f}, среднее(ноль)={mid:.3f}")

# --- 4 + 5. Сдвиг к нулю + модуль ---
df_cut['Shifted']   = df_cut['Value'] - mid
df_cut['Rectified'] = df_cut['Shifted'].abs()


# --- 6. График ---
fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True)

# (а) исходные обрезанные данные с линией "ноль"
axes[0].plot(df_cut['Minutes'], df_cut['Value'], linewidth=0.7, color='steelblue')
axes[0].axhline(mid, color='red', linestyle='--', linewidth=1, label=f'нулевая линия (среднее) = {mid:.2f}')
axes[0].set_ylabel('Value (исходное)')
axes[0].set_title('Обрезано с максимума — исходные данные')
axes[0].legend(loc='upper right')
axes[0].grid(alpha=0.3)

# (б) после сдвига — видно как крутится вокруг нуля
axes[1].plot(df_cut['Minutes'], df_cut['Shifted'], linewidth=0.7, color='darkorange')
axes[1].axhline(0, color='red', linestyle='--', linewidth=1)
axes[1].set_ylabel('После сдвига')
axes[1].set_title('Центрировано вокруг 0')
axes[1].grid(alpha=0.3)

# (в) после модуля — всё вверх
axes[2].plot(df_cut['Minutes'], df_cut['Rectified'], linewidth=0.7, color='seagreen')
axes[2].axhline(0, color='red', linestyle='--', linewidth=1)
axes[2].set_ylabel('|значение|')
axes[2].set_xlabel('Minutes (от точки максимума)')
axes[2].set_title('Отражено: отрицательные значения перевёрнуты вверх')
axes[2].grid(alpha=0.3)

df_cut['Rec_rol_max'] = df_cut['Rectified'].rolling(window=20, min_periods=1).max()

df_cut['smoothed_with_savgol'] = savgol_filter(df_cut['Rec_rol_max'],
                                        window_length=10,
                                        polyorder=3,
                                        mode='nearest')

axes[3].plot(df_cut['Minutes'], df_cut['Rec_rol_max'], linewidth=0.7, color='red')
axes[3].plot(df_cut['Minutes'], df_cut['smoothed_with_savgol'], linewidth=4, color='navy')
axes[3].axhline(0, color='red', linestyle='--', linewidth=1)
axes[3].set_ylabel('|значение|')
axes[3].set_xlabel('Minutes (от точки максимума)')
axes[3].set_title('Отражено: отрицательные значения перевёрнуты вверх + максимумы')
axes[3].grid(alpha=0.3)

plt.tight_layout()

plt.show()