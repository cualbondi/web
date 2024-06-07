CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE OR REPLACE FUNCTION
    min_linestring ( "line1" Geometry, "line2" Geometry )
    RETURNS geometry
    AS $$
    BEGIN
        IF ST_Length2D_Spheroid(line1, 'SPHEROID["GRS_1980",6378137,298.257222101]') < ST_Length2D_Spheroid(line2, 'SPHEROID["GRS_1980",6378137,298.257222101]') THEN
            RETURN line1;
        ELSE
            RETURN line2;
        END IF;
    END;
    $$ LANGUAGE plpgsql;

DROP AGGREGATE IF EXISTS min_path(Geometry);

CREATE AGGREGATE min_path(Geometry)(SFUNC = min_linestring, STYPE = Geometry);