import os
from bs4 import BeautifulSoup, SoupStrainer
import requests


for url, path in [("http://viewfinderpanoramas.org/Coverage%20map%20viewfinderpanoramas_org3.htm",
                   "/media/ronny/Backup500GB/srtm/3/"), 
                  ("http://viewfinderpanoramas.org/Coverage%20map%20viewfinderpanoramas_org1.htm",
                   "/media/ronny/Backup500GB/srtm/1/")]:
    page = requests.get(url)    
    data = page.text
    soup = BeautifulSoup(data)
    os.chdir(path)
    for link in soup.find_all(href=True):
        lname = link.get('href')
        fname = lname.rsplit("/", 1)[-1]
        if not os.path.exists(fname) and not fname.endswith(".html") and not len(fname) < 3:
            print(f"will download {fname} from {lname}")
            #file_name = wget.download(site_url)
            os.system(f"wget {lname}")
            
            os.system(f"unzip {fname} && rm {fname} && touch {fname}")  # create the empty zip file after extraction to not download again
            fname_new = fname.replace('.zip', '/*')
            os.system(f"mv {fname_new} . && rm -r {fname_new[:-1]}")

print("finished")

        
