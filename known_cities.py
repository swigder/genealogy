import unidecode

COUNTRIES_TO_COUNTIES_TO_CITIES = {
    'Hungary': {
        'Borsod-Abaúj-Zemplén': [
            ['Mezőcsát', 'Mezo-Csath'],
        ],
        'Csongrád-Csanád': [
            'Szeged',
        ],
        'Fejér': [
            'Kápolnásnyék',
            'Kisvelence',
        ],
        'Hajdú-Bihar': [
            'Debrecen'
        ],
        'Jász-Nagykun-Szolnok': [
            'Tiszafüred',
        ],
        'Szabolcs-Szatmár-Bereg': [
            'Balkány',
            'Kisvárda',
            'Mátészalka',
            'Nyiregyhaza'
            'Nyírmada',
        ],
        'Vas': [
            'Nagyrákos',
        ],
    },
    'Romania': {
        'Bihor': [
            ['Oradea', 'Nagyvarad'],
        ],
        'Cluj': [
            ['Cluj-Napoca', 'Kolozsvár', 'Cluj'],
            ['Dej', 'Dees'],
        ],
        'Maramureș': [
            ['Sighetu Marmației', 'Sighetu'],
        ],
        'Sălaj': [
            ['Șimleu Silvaniei', 'Szilágysomlyó'],
            ['Cehei', 'Somlyocsehi'],
            ['Uileacu Șimleului', 'Somlyóújlak']
        ],
        'Satu Mare': [
            ['Giorocuta', 'Girókuta'],
            ['Satu Mare', 'Szatmar', 'Szatmárnémeti'],
        ],
    },
    'Slovakia': {
        'Košice-okolie': [
            ['Herľany', 'Rankfüred'],
            ['Vyšná Kamenica', 'Felsőkemence'],
        ]
    },
    'Ukraine': {
        'Zakarpattia Oblast': [
            'Bushtyno',
            ['Solotvyno', 'Falu-Szlatina', 'Szlatina']
        ]
    },
}

KNOWN_CITIES = {}

for country, counties in COUNTRIES_TO_COUNTIES_TO_CITIES.items():
    for county, cities in counties.items():
        for city in cities:
            city_names = [city] if isinstance(city, str) else city
            city_modern_name = city_names[0]
            for city_name in city_names:
                KNOWN_CITIES[unidecode.unidecode(city_name)] = {'city': city_modern_name, 'state': county,
                                                                'country': country}
