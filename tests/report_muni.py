import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

class ReportGenerator:
    def __init__(self,title, title_graph, data1, data2, params,visc, filename):
        if (params["type"] == "Вязкость"):
            self.title = title
        else:
            self.title = f"Определение характеристик подвулканизации по <br />{params["standart"]}. Вискозиметр Mooney 1500S."
        self.viscosity = visc
        self.min_visc = 0
        self.t5 = 0
        self.t35 = 0
        self.title_graph = title_graph
        self.data1 = data1
        self.data2 = data2
        self.params = params
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name='Centered', alignment=1))
        pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
        self.styles['Title'].fontName = 'Arial'
        self.styles['Title'].fontSize = 18
        self.styles['Title'].spaceAfter = 10
        plt.rcParams.update({'font.size': 14})
        self.custom_style = ParagraphStyle(
            name='CustomStyle',
            fontName='Arial',  
            fontSize=14,
            spaceAfter=12  # Отступ после параграфа
        )

    def calculate_params_podvulk(self):
        df = pd.DataFrame({"time": self.data1, "values": self.data2})
        df = df[df["time"] > 1.1]
        if not df.empty:
            min_index = df["values"].idxmin()
        else:
            return
        self.min_visc = df.loc[min_index, "values"]
        min_visc_time = df.loc[min_index, "time"]
        df = df[df["time"] > min_visc_time]
        mask_t5 = df["values"] > self.min_visc + 5
        mask_t35 = df["values"] > self.min_visc + 35
        if mask_t5.any():
            idx_value_5 = df[mask_t5].idxmin()
            self.t5 = df.loc[idx_value_5, "time"].iloc[0]
            self.t5 = round(self.t5, 2)
        else: 
            return
        if mask_t35.any():
            idx_value_35 = df[mask_t35].idxmin()
            self.t35 = df.loc[idx_value_35, "time"].iloc[0]
            self.t35 = round(self.t35, 2)
        else:
            return

    def build_pdf_report(self):
        doc = SimpleDocTemplate(
            self.filename,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )
        
        elements = []
        
        # Заголовок отчета
        elements.append(Paragraph("ООО «НИИЭМИ»", self.styles["Title"]))
        elements.append(Paragraph(self.title, self.styles["Title"]))
        
        # Таблица 4 столбца и 2 строки
        data = [["Дата испытания", "Время испытания", "Марка смеси", "Откуда поступил"],
                [self.params['Date'], self.params['Time'], self.params['Material'], self.params['From_lab']]]
        table = Table(data)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 5),   # Отступ сверху
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10) # Отступ снизу
        ]))
        elements.append(table)

        elements.append(Spacer(1,20))
        # Добавление графика
        img = Image('plot.png', width=16*cm, height=12*cm)  # Устанавливаем размеры изображения
        elements.append(img)


        elements.append(Paragraph(f"Технические характеристики испытания", self.styles["Title"]))      

        # Вторая таблица 2 столбца и 5 строк
        if (self.params["type"] == "Подвулканизация"):
            self.calculate_params_podvulk()
            data2 = [["Размер ротора", self.params['Rotor_size']],
                    #["Время предварительного прогрева, мин", self.params['time_warm']],
                    ["Температура испытания, С", self.params['temperature']],
                    #["Продолжительность испытания, мин", self.params['time_test']],
                    ["Минимальная вязкость по Муни, усл.ед", round(self.min_visc)],
                    ["t5, мин", self.t5],
                    ["t35, мин", self.t35],
                    ["Индекс вулканизации", round(self.t35 - self.t5, 2)],
                    ]
        else:
            data2 = [["Размер ротора", self.params['Rotor_size']],
                    ["Время предварительного прогрева, мин", self.params['time_warm']],
                    ["Температура испытания, С", self.params['temperature']],
                    ["Продолжительность испытания, мин", self.params['time_test']],
                    ["Число единиц по Муни, усл.ед", self.viscosity]]
        table2 = Table(data2,colWidths=[350,100])
        table2.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Arial'), 
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 5),   # Отступ сверху
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5) # Отступ снизу

        ]))
        elements.append(table2)
        elements.append(Spacer(1,12))
        elements.append(Paragraph("Испытание провел ______________ (подпись и дата)", self.custom_style))
        elements.append(Paragraph("Руководитель сектора №1 ______________ (подпись и дата)", self.custom_style))
        # Завершение отчета
        try:
            doc.build(elements)
        except:
            return None

# Пример использования
if __name__ == "__main__":
    # Данные для графика
    visc = 2
    data1 = [0.4, 0.9, 1, 2, 4.5,8,9,10,11,12,13,14,15,16,17]
    data2 = [2, 3, 5, 7, 11, 12,9,10,11,12,13,14,15,16,17]
    params = {
            "com_port": 'COM7',
            "boudrate": 9600,
            "address": 16,
            "poll_int": 5,
        #Настройки испытания:    
            "Date": None,
            "Time": None,
            "Material": None,
            "From_lab": None,
            "Rotor_size": "Б",
            "time_warm": 1,
            "temperature": None,
            "time_test": 0,
            "viscosity": None,
            "time_viscosity": 0,
            "tol_viscosity": 0.09,    
            "standart": "ГОСТ Р 54552-2011",
            "type": "Подвулканизация"             
        }
    report = ReportGenerator("Определение вязкости по Муни по ГОСТ 10722-76 \n вязкозиметр","Вязкость по Муни", data1, data2, params, visc, r"hello.pdf")
    report.build_pdf_report()