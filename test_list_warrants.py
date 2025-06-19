from warrant_scraper import get_all_warrants
import pandas as pd

warrants = get_all_warrants()
print(type(warrants))
print(warrants.head(10))
if isinstance(warrants, pd.Series):
    print('Series name:', warrants.name)
    print('Series values:', warrants.values[:10])
elif isinstance(warrants, pd.DataFrame):
    print('DataFrame columns:', warrants.columns)
    print(warrants.info())
else:
    print('Object:', warrants)
