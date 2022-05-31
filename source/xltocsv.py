import pandas

data = pandas.read_excel("./data/my19yielddata.xlsx")
data.to_csv("./data/my19yielddata.csv")