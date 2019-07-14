import geopandas as gpd
from django.db import connection
from psycopg2.extras import execute_values
from .logging import logger


class CrossAreasTask:
    def run(self):
        cu = connection.cursor()

        crs = {"init": "epsg:4326"}

        logger.info("Cross osm recorridos")
        logger.info("Obteniendo bus routes de osm planet_osm_line")

        bus_routes = gpd.read_postgis(
            """
                    # esto cambiarlo para no usar mas planet_osm_line (osm2pgsql), usar osmosis para construir las bus_routes
                    # SELECT
                    #     @osm_id AS osm_id, -- @=modulus operator
                    #     name,
                    #     ref,
                    #     st_linemerge(st_union(way)) AS way
                    # FROM
                    #     planet_osm_line
                    # WHERE
                    #     route = 'bus'
                    # GROUP BY
                    #     osm_id,
                    #     name,
                    #     ref
                """,
            connection,
            geom_col="way",
            crs=crs,
        )
        bus_routes.set_index("osm_id", inplace=True)

        logger.info("Creando geodataframe")
        bus_routes_buffer = gpd.GeoDataFrame(
            {
                "osm_id": bus_routes.index,
                "way": bus_routes.way,
                "way_buffer_40": bus_routes.way.buffer(0.0004),
                "way_buffer_40_simplify": bus_routes.way.simplify(0.0001).buffer(
                    0.0004
                ),
                "name": bus_routes.name,
            },
            crs=crs,
        ).set_geometry("way_buffer_40_simplify")

        logger.info("Obteniendo recorridos de cualbondi core_recorridos")
        core_recorrido = gpd.read_postgis(
            """
                    SELECT
                        cr.id,
                        cr.nombre,
                        cr.linea_id,
                        cr.ruta,
                        cl.nombre AS linea_nombre
                    FROM
                        core_recorrido cr
                        JOIN core_linea cl ON (cr.linea_id = cl.id)
                    --  JOIN catastro_ciudad_recorridos ccr ON (ccr.recorrido_id = cr.id)
                    --WHERE
                    --    ccr.ciudad_id = 1
                    ;
                """,
            connection,
            geom_col="ruta",
            crs=crs,
        )
        core_recorrido.set_index("id", inplace=True)

        logger.info("Creando geodataframe para cb con buffers")
        core_recorrido_buffer = gpd.GeoDataFrame(
            {
                "id": core_recorrido.index,
                "ruta": core_recorrido.ruta.simplify(0.0001),
                "ruta_buffer_40_simplify": core_recorrido.ruta.simplify(0.0001).buffer(
                    0.0004
                ),
                "nombre": core_recorrido.nombre,
                "linea_id": core_recorrido.linea_id,
            },
            crs=crs,
        ).set_geometry("ruta")

        logger.info("Generando intersecciones")
        intersections = gpd.sjoin(
            core_recorrido_buffer, bus_routes_buffer, how="inner", op="intersects"
        )

        logger.info("Copiando indice, id")
        intersections["id"] = intersections.index

        logger.info("Copiando indice, osm_id")
        intersections["osm_id"] = intersections.index_right

        logger.info("Drop indice, osm_id")
        intersections.drop("index_right", inplace=True, axis=1)

        logger.info("Generando match [id, osm_id]")
        intersections = intersections[["id", "osm_id"]]

        logger.info("Generando indice de match [id, osm_id]")
        intersections.index = range(len(intersections))

        logger.info("Generando way_buffer_40_simplify")
        way_buffer_40_simplify = gpd.GeoSeries(
            bus_routes_buffer.loc[intersections.osm_id].way_buffer_40_simplify.values,
            crs=crs,
        )

        logger.info("Generando ruta_buffer_40_simplify")
        ruta_buffer_40_simplify = gpd.GeoSeries(
            core_recorrido_buffer.loc[intersections.id].ruta_buffer_40_simplify.values,
            crs=crs,
        )

        logger.info("Generando symmetric_difference")
        diffs = ruta_buffer_40_simplify.symmetric_difference(
            way_buffer_40_simplify
        ).area.values

        logger.info("Generando norm_factor")
        norm_factor = (
            ruta_buffer_40_simplify.area.values + way_buffer_40_simplify.area.values
        )

        logger.info("Generando diffs")
        diffs = (diffs / norm_factor).tolist()

        logger.info("Pasando osm_ids a lista")
        osm_ids = intersections.osm_id.values.tolist()

        logger.info("Pasando osm_names a lista")
        osm_names = bus_routes.loc[osm_ids].name.values.tolist()
        # ways = bus_routes.loc[osm_ids].way.map(lambda x: x.wkb).values.tolist()

        logger.info("Pasando recorrido_ids de intersections a lista")
        recorrido_ids = intersections["id"].values.tolist()

        logger.info("Pasando linea_ids a lista")
        linea_ids = core_recorrido.loc[recorrido_ids].linea_id.values.tolist()
        # rutas = core_recorrido.loc[recorrido_ids].ruta.map(lambda x: x.wkb).values.tolist()

        logger.info("Pasando recorrido_nombres a lista")
        recorrido_nombres = core_recorrido.loc[recorrido_ids].nombre.values.tolist()
        # ruta_buffer_40_simplifys = ruta_buffer_40_simplify.map(lambda x: x.wkb).values.tolist()
        # way_buffer_40_simplifys = way_buffer_40_simplify.map(lambda x: x.wkb).values.tolist()

        logger.info("Pasando linea_nombres a lista")
        linea_nombres = core_recorrido.loc[recorrido_ids].linea_nombre.values.tolist()

        logger.info("DROP TABLE crossed_areas")
        cu.execute("DROP TABLE IF EXISTS crossed_areas;")
        cu.execute("DROP INDEX IF EXISTS crossed_areas_recorrido_id;")
        cu.execute("DROP INDEX IF EXISTS crossed_areas_area;")

        logger.info("CREATE TABLE crossed_areas")
        cu.execute(
            """
                    CREATE TABLE crossed_areas (
                        area FLOAT,
                        linea_id INTEGER,
                        recorrido_id INTEGER,
                        osm_id BIGINT,
                        linea_nombre VARCHAR(100),
                        recorrido_nombre VARCHAR(100),
                        osm_name TEXT
                    );
                """
        )

        logger.info("Preparando lista de values")
        data = list(
            zip(
                diffs,
                linea_ids,
                recorrido_ids,
                osm_ids,
                linea_nombres,
                recorrido_nombres,
                osm_names,
            )
        )

        logger.info("Ejecutando insert query")
        insert_query = """
                INSERT INTO crossed_areas (
                    area,
                    linea_id,
                    recorrido_id,
                    osm_id,
                    linea_nombre,
                    recorrido_nombre,
                    osm_name
                )
                VALUES %s
            """
        execute_values(cu, insert_query, data)

        logger.info("Commit insert query")
        connection.commit()

        logger.info("Generando indice crossed_areas_recorrido_id")
        cu.execute(
            "CREATE INDEX crossed_areas_recorrido_id ON crossed_areas (recorrido_id);"
        )
        cu.execute("CREATE INDEX crossed_areas_area ON crossed_areas (area);")

        logger.info("LISTO!")
