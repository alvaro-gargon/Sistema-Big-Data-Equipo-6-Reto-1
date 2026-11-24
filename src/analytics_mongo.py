from pymongo import MongoClient
import config

cliente = MongoClient(config.CONEXIONMONGO)
db = cliente[config.BD]
coleccion = db[config.COLECCION]


def tiempo_medio_estancia():

    pipeline = [
        {
            "$project": {
                "categoria": "$triaje_manchester.categoria_patologia",
                "tiempo_estancia": {
                    "$divide": [
                        {
                            "$subtract": [
                                "$timestamp_alta",
                                "$timestamp_llegada"
                            ]
                        },
                        60000
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$categoria",
                "tiempo_medio": {
                    "$avg": "$tiempo_estancia"
                }
            }
        },
        {
            "$sort": {
                "_id": 1
            }
        }
    ]

    resultado = coleccion.aggregate(pipeline)

    return list(resultado)


def distribucion_destinos_edad():

    pipeline = [
        {
            "$project": {
                "grupo_edad": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {"$lt": ["$edad", 18]},
                                "then": "Menor de 18"
                            },
                            {
                                "case": {
                                    "$and": [
                                        {"$gte": ["$edad", 18]},
                                        {"$lte": ["$edad", 64]}
                                    ]
                                },
                                "then": "Entre 18 y 64"
                            },
                            {
                                "case": {"$gte": ["$edad", 65]},
                                "then": "Igual o superior a 65"
                            }
                        ],
                        "default": "Otro grupo"
                    }
                },
                "destino": "$destino_alta"
            }
        },
        {
            "$group": {
                "_id": {
                    "grupo_edad": "$grupo_edad",
                    "destino": "$destino"
                },
                "cantidad": {
                    "$sum": 1
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.grupo_edad",
                "total": {"$sum": "$cantidad"},
                "destinos": {
                    "$push": {
                        "destino": "$_id.destino",
                        "cantidad": "$cantidad"
                    }
                }
            }
        },
        {
            "$unwind": "$destinos"
        },
        {
            "$project": {
                "grupo_edad": "$_id",
                "destino": "$destinos.destino",
                "porcentaje": {
                    "$multiply": [
                        {
                            "$divide": [
                                "$destinos.cantidad",
                                "$total"
                            ]
                        },
                        100
                    ]
                }
            }
        },
        {
            "$sort": {
                "grupo_edad": 1,
                "destino": 1
            }
        }
    ]

    resultado = coleccion.aggregate(pipeline)

    return list(resultado)