import requests
import json
import re
from urllib.parse import quote
import random

import translator_constants as TC

# https://gist.github.com/Roadcrosser/e08ecf22d3e14dc555b15bfe8d46243c

class Translator(object):
    def __init__(self, service_urls=None):
        self.service_urls = service_urls or ['translate.google.com'] # self.DEFAULT_SERVICE_URLS
        
    def generateBaseUrl(self, i=0):
        return f"https://{self.service_urls[i]}/_/TranslateWebserverUi/data/batchexecute?rpcids=MkEWBc&rt=c&bl=boq_translate-webserver_20201110.10_p0"

    @staticmethod
    def flattenList(l):
        """
        Flattens a list of nested lists
        """
        o = []
        
        for li in l:
            if type(li) is list:
                o.extend(Translator.flattenList(li))
            else:
                o.append(li)
        
        return o
    
    def translate(self, query, target='en', source='auto', detailed=False):
        for i in range(len(self.service_urls)):
            try:
                url = self.generateBaseUrl(i)

                # This is arcane
                req = json.dumps([[query, source, target, True], [None]])
                req = [[["MkEWBc", req, None, "generic"]]]
                req = "f.req=" + quote(json.dumps(req)) # URL encode this

                r = requests.post(url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=req)

                # Get the first number string
                num_match = re.search(r"\n(\d+)\n", r.text)

                # Find where the numbers end
                front_pad = num_match.span()[1]
                # The number tells us how many characters the next json block has
                end_num = front_pad + int(num_match.groups()[0]) - 1

                # Lots of arcane json processing. I recommend looking at the data in transit in a JSON viewer because I have no idea what is what.
                data = json.loads(r.text[front_pad:end_num])
                data = data[0][2]
                data = json.loads(data)
                data = data

                resp = data[1][0]

                if detailed:
                    ret_source = data[0][2]
                    ret_source = ret_source if ret_source else source

                    ret_target = data[1][1]

                    metadata = {
                        'source'   : ret_source,
                        'target'   : ret_target,
                        'raw_resp' : resp,
                    }

                    ret = []
                    if (len(resp) > 1):
                        # For the case where feminine and masculine versions of the translation are returned.
                        metadata['parsed_resp'] = [f"{i[0]}\n{i[2]}" for i in resp]
                        metadata['resp'] = "\n\n".join(metadata['parsed_resp'])
                    else:
                        # metadata['parsed_resp'] = self.flattenList(resp[0][5])
                        metadata['parsed_resp'] = [[option for option in self.flattenList(sentence) if type(option) is str] for sentence in metadata['raw_resp'][0][5]]
                        # metadata['resp'] = metadata['parsed_resp'][0]
                        metadata['resp'] = " ".join([options[0] for options in metadata['parsed_resp']])

                    # metadata['resp'] = "\n\n".join(metadata['parsed_resp'])

                    return metadata
                else:
                    # Get the actual translations.
                    # There may be other cases or word arrangements I'm not aware of so the following may be incomplete.
                    ret = []
                    if (len(resp) > 1):
                        # For the case where feminine and masculine versions of the translation are returned.
                        ret += [f"{i[0]}\n{i[2]}" for i in resp]
                    else:
                        # Default case. I'm actually throwing away some "suggested translations" that you may want.
                        ret += [resp[0][5][0][0]]

                    return "\n\n".join(ret)
            except:
                pass

if __name__ == "__main__":
    translator = Translator(['translate.google.ca'])

    query = """太平洋は地球表面のおよそ3分の1を占め、その面積はおよそ1億7970万平方キロメートルである。これは世界の海の総面積の46%を占め、また地球のすべての陸地を足したよりも広い[1]。また、日本列島のおよそ473倍の面積である。

北極のベーリング海から南極海の北端である南緯60度（古い定義では南極大陸のロス海までだった）まで、およそ1万5500キロメートルある。太平洋は北緯5度ぐらい、つまりおおよそインドネシアからコロンビアとペルーの海岸線までの辺りで東西方向の幅が一番大きいおよそ1万9800キロメートルになる。これは地球の半周とほぼ同じ長さで、地球の衛星である月の直径の5倍以上の長さである。また、現在分かっているうちで地球上で一番深いところであるマリアナ海溝は太平洋にあり、その深さは海面下1万911メートルである。太平洋の平均深度は4028メートルから4188メートルである[1]。

太平洋には2万5000もの島がある。これは、太平洋以外の海にある島をすべて合計した数よりも多い。大部分は赤道より南にある。部分的に沈んでいる島も含めて、その数は継続的に多くなっている。"""
    
    print(translator.translate(query))
    # query = "translifier"

    # query = query.replace('’', "'")
    # query = query.replace('“', '"')
    # query = query.replace('”', '"')

    # res = translator.translate(query, detailed=True)['resp']

    # print("*** ORIGINAL TRANSLATION ***")
    # print(res)
    # print("****************************")
    # print()

    # N = 5
    # all_langs = list(TC.LANGUAGES.keys())
    # langs = [all_langs[int(i)] for i in random.sample(range(len(all_langs)), N)]

    # for idx, lang in enumerate(langs):
    #     res_tmp = translator.translate(res, target=lang, source='auto', detailed=True)
    #     if res_tmp is None:
    #         langs.remove(lang)
    #     else:
    #         res = res_tmp['resp']

    #     # print(f"*** LANG {lang}/{TC.LANGUAGES[lang]} ***")
    #     # print(res)
    #     # print("*** *** *** ***")

    # res = translator.translate(res, target='en', source='auto', detailed=True)['resp']

    # print("*** REPEATED TRANSLATION ***")
    # print(" -> ".join(langs))
    # print(" -> ".join([TC.LANGUAGES[lang].capitalize() for lang in langs]))
    # print("****************************")
    # print(res)

    # print(res['resp'])