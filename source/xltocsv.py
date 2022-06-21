import pandas

whichMold = "my33"
data = pandas.read_excel(f"./data/{whichMold}yielddata.xlsx")
data.to_csv(f"./data/{whichMold}yielddata.csv")