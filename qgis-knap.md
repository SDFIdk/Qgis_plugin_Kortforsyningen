# QGIS Kortforsyning knap

Følgende dokument beskriver hvordan kortforsynings knappen holdes opdateret og
driftes i praksis.

Knappen forventer to online resourcer. Et json dokument som definerer de
forskellige kategorier, samt et HTML dokument som definerer indholdet af 'Om
pluginet' dialogen.

## Kategorier

En kategori er en QGIS projekt fil, som kan indeholde et vilkårligt antal lag.
JSON strukturen er som set nedenfor. `url` er der hvor pluginet henter QGIS
projekt filen, og `name` definerer navnet på kategorien i knappen.

```json
{
  "categories": [
    {
      "url": "http://labs-develop.septima.dk/qgis-kf-knap/Baggrundskort.qgs",
      "name": "Baggrundskort"
    },
    {
      "url": "http://labs-develop.septima.dk/qgis-kf-knap/HistoriskeBaggrundskort.qgs",
      "name": "Historiske kort"
    },
    {
      "url": "http://labs-develop.septima.dk/qgis-kf-knap/DHM.qgs",
      "name": "Højdemodel"
    }
  ]
}
```

Her eksemplificeret med *Baggrundskort*, hvor *Baggrundskort.qgs* indeholder 6 lag. Disse præsenteres i knappen med de i QGIS angivne navne.

![](http://telling.xyz/uploads/NylmHU1Ffg.png)

Inden man offentliggører sin QGIS projekt fil, er det væsentligt at man udskifter password og brugernavn i filen. Åbnes QGIS projektet i en tekst editor, skal der i datasource elementerne udskiftes kodeord og brugernavn til udskiftnings variablene `{{kf_username}}` og `{{kf_password}}`

For et QGIS projekt med brugernavn `septima` og kodeord `kodeord` vil strengen se således ud:

```sh
<datasource>SmoothPixmapTransform=1&amp;contextualWMSLegend=0&amp;crs=EPSG:25832&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;layers=dtk_skaermkort_daempet&amp;styles=&amp;url=http://kortforsyningen.kms.dk/?servicename%3Dtopo_skaermkort%26client%3DQGIS%26version%3D1.1.1%26login%3Dseptima%26password%3Dkodeord</datasource>
```

Efter erstatning, ser den ud som:

```sh
<datasource>SmoothPixmapTransform=1&amp;contextualWMSLegend=0&amp;crs=EPSG:25832&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;layers=dtk_skaermkort_daempet&amp;styles=&amp;url=http://kortforsyningen.kms.dk/?servicename%3Dtopo_skaermkort%26client%3DQGIS%26version%3D1.1.1%26login%3D{{kf_username}}%26password%3D{{kf_password}}</datasource>
```

I QGIS hentes kategori filerne i det tilfælde de lokale versioner er ældre end 12 timer.

## 'Om pluginet' dialog

Dialogen 'Om pluginet' afhænger af en ekstern HTML kilde. Der her tale om simpel HTML, det er derfor ikke muligt at bruge eksterne stylesheets mm. HTML filen downloades ligeledes kun hvis den lokale version er ældre end 12 timer.
