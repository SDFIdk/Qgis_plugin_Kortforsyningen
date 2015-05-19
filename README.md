# QGIS KF-Knappen
Kortforsyningen knap til QGIS, som gør det nemmere at tilføje wms fra
kortforsyningen.

## Til udvikling
Det er nødvendigt at oversætte qgis resource filerne førend pluginnet
overhovedet lader sig loade i QGIS. Kør derfor `make` én gang. Herefter kan man
med fordel symlinke fra sit git repo til `~/.qgis2/python/plugins`.


```sh
ln -s ~/Code/qgis-kf-knappen/Kortforsyningen ~/.qgis2/python/plugins
```