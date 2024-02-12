# gtfs-headway-explorer
Identify route headway from GTFS dataset by user defined time of day (TOD)

## Description
Transportation modelers frequently update transit networks and parameters to keep the model parameters up to date. This repository utilizes General Transit Feed Specification (GTFS) data provided by transit agencies to determine route headways based on Time of Day (TOD). The automation included here calculates headway by dividing the time duration by the number of buses arriving at the same stop within a specific TOD. The shape data is also read to generate itineraries that can be compared with the existing model network. This process aids in ensuring that the transit model aligns closely with the latest transit conditions and provides a valuable tool for transportation planning and analysis.

## Getting Started

### Dependencies

* Python 3
* GTFS dataset
* Background map (shapefile format)

### Installing

* Clone the repository

### Executing program
```
python gtfs_headway_plots.py
```

## Help
Look through the code comments


## Authors

Cherry Liu, South East Michigan Council of Governments. 

cliu@semcog.org

## Version History

* 1.0
    * Initial Release
