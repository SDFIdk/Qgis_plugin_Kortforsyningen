# Kortforsyningspluginet til QGIS 2
Et plugin til QGIS 2 (fx 2.14, 2.18), der gør det let at tilføje lag fra
kortforsyningen til QGIS.
Pluginet kan hentes direkte fra QGIS gennem det officielle repository, eller kan downloades her fra GitHub.

Fejl rapporteres i <a href="https://github.com/Kortforsyningen/Qgis_plugin_Kortforsyningen/issues"> issue tracker </a>

# Kortforsyningspluginet til QGIS 3
Kortforsyningspluginet findes også til QGIS 3. Dette har sit eget <a href="https://github.com/Kortforsyningen/Qgis_plugin_Kortforsyningen_v3">GitHub repository.</a>

## Til udvikling
Det er nødvendigt at oversætte qgis resource filerne førend pluginnet
overhovedet lader sig loade i QGIS. Kør derfor `make` én gang. Herefter kan man
med fordel symlinke fra sit git repo til `~/.qgis2/python/plugins`.


```sh
ln -s ~/Code/qgis-kf-knappen/Kortforsyningen ~/.qgis2/python/plugins
```
