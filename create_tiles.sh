#!/bin/bash

WORK_DIR=/tmp/tiles/
SRTM_BASE_1=/mnt/backup500/srtm/1/
SRTM_BASE_3=/mnt/backup500/srtm/3/
DEST_DIR=/mnt/backup500/srtm/tiles/   # if changed, adjust TILES_FOLDERS in my_base.py

mkdir -p "${WORK_DIR}" "${DEST_DIR}"

create_individual_tifs() {
  local srtm_base="$1"
  shift   # remove first parameter
  local base_names=("$@") # Capture all arguments as an array
  for base in "${base_names[@]}"; do
    cmd="gdal_translate ${srtm_base}${base}.hgt.zip ${WORK_DIR}${base}.tif"
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}
  done
}

process_area() {
  if [[ $1 != true && $1 != 1 ]]; then return; fi
  shift
  local srtm_base="$1"
  shift

  # Get all the the dynamic ranges
  local ranges=()
  while [[ "$1" != "" ]]; do
    if [[ "$1" == N* || "$1" == S* ]]; then
      break
    fi
    ranges+=("$1")
    shift
  done

  local base_names=("$@") # Remaining htg names

  create_individual_tifs "${srtm_base}" "${base_names[@]}"

  # merge
  all_tifs=""
  for base in "${base_names[@]}"; do
    all_tifs="${all_tifs} ${WORK_DIR}${base}.tif"
  done
  rm -f "${WORK_DIR}merged.tif"
  cmd="gdal_merge.py -o ${WORK_DIR}merged.tif ${all_tifs}"
  echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
  ${cmd}
  rm -f "${all_tifs}"

  for dynamic_range in "${ranges[@]}"; do
    # Create the tiles
    IFS='_' read -r start end _ <<< "${dynamic_range}"
    rm -f "${WORK_DIR}merged_8bit.tif"
    cmd="gdal_translate -ot Byte -scale ${start} ${end} ${WORK_DIR}merged.tif ${WORK_DIR}merged_8bit.tif"
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}

#    cmd="gdal2tiles.py -z 5-10 -tms ${WORK_DIR}merged_8bit.tif ${WORK_DIR}tiles_${dynamic_range}"   # quick
    cmd="gdal2tiles.py -z 5-13 -tms ${WORK_DIR}merged_8bit.tif ${WORK_DIR}tiles_${dynamic_range}"   # normal
    echo "$(date '+%Y-%m-%d %H:%M:%S') executing ${cmd}"
    ${cmd}

    echo "$(date '+%Y-%m-%d %H:%M:%S') clearing empty tiles and storing tiles in ${DEST_DIR}"
    find "${WORK_DIR}tiles_${dynamic_range}" -type f -size -700c -delete
    if [[ "${WORK_DIR}" != "${DEST_DIR}" ]]; then
      rsync -au "${WORK_DIR}tiles_${dynamic_range}" "${DEST_DIR}"
      rm -r "${WORK_DIR}tiles_${dynamic_range}"
    fi
  done
}

# Give the following parameters:
#  - true or 1 to process the area
#  - srtm 1 or 3 resolution
#  - all the dynamic ranges for the tiles in the form <min>_<max>
#    - the png will be stored as 8 bit, e.g. 256 different grey scales
#  - all the base names for the htg.zip files

# UK
process_area 0 $SRTM_BASE_3 "0_255" "0_1023" \
  "N49W006" \
  "N50E000" "N50E001" "N50W001" "N50W002" "N50W003" "N50W004" "N50W005" "N50W006" \
  "N51E000" "N51E001" "N51W001" "N51W002" "N51W003" "N51W004" "N51W005" \
  "N52E000" "N52E001" "N52W001" "N52W002" "N52W003" "N52W004" "N52W005" \
  "N53E000" "N53W001" "N53W002" "N53W003" "N53W004" "N53W005" \
  "N54W001" "N54W002" "N54W003" "N54W004" "N54W005" \
  "N55W002" "N55W003" "N55W004" "N55W005" "N55W006" "N55W007" \
  "N56W003" "N56W004" "N56W005" "N56W006" "N56W007" \
  "N57W003" "N57W004" "N57W005" "N57W006" "N57W007" \
  "N58W003" "N58W004" "N58W005" "N58W006" "N58W007"

# La Palma
process_area 0 $SRTM_BASE_3 "0_255" "0_1023" "0_4095" "1024_3071" \
  "N28W017" "N28W018" "N28W019"

# Norway
process_area 0 $SRTM_BASE_3 "0_255" "0_1023" \
  "N68E018" "N68E019" "N68E020" \
  "N69E018" "N69E019" "N69E020"

# Sweden
process_area 0 $SRTM_BASE_3 "0_255" \
  "N55E013" "N55E014" \
  "N56E013" "N56E014" "N56E015" "N56E016" \
  "N57E011" "N57E012" "N57E013" "N57E014" "N57E015" "N57E016" \
  "N58E012" "N58E013" "N58E014" "N58E015" "N58E016" "N58E017" \
  "N59E013" "N59E014" "N59E015" "N59E016" "N59E017" "N59E018"

# Slowakia/Cech
process_area 0 $SRTM_BASE_3 "0_1023" \
  "N48E016" "N48E017" "N48E018" "N48E019" "N48E020" \
  "N49E014" "N49E015" "N49E016" "N49E017" "N49E018" "N49E019" "N49E020" \
  "N50E014" "N50E015"

# High Tatra
process_area 0 $SRTM_BASE_3 "0_4095" \
  "N49E019" "N49E020"

# Brittany
process_area 0 $SRTM_BASE_3 "0_255" \
 "N48W002" "N48W003" "N48W004" "N48W005"

# Mecklenburg Vorpommern
process_area 0 $SRTM_BASE_3 "0_255" \
  "N53E013" "N54E013"

# Deutschland
process_area 1 $SRTM_BASE_3 "0_255" "0_1023" \
  "N47E007" "N47E008" "N47E009" "N47E010" "N47E011" "N47E012" \
  "N48E007" "N48E008" "N48E009" "N48E010" "N48E011" "N48E012" \
  "N49E007" "N49E008" "N49E009" "N49E010" "N49E011" "N49E012" \
  "N50E007" "N50E008" "N50E009" "N50E010" "N50E011" "N50E012" "N50E013" \
  "N51E006" "N51E007" "N51E008" "N51E009" "N51E010" "N51E011" "N51E012" "N51E013" "N51E014"

# Alps
process_area 0 $SRTM_BASE_3 "0_4095" "0_2047" "2048_4095" \
  "N46E006" "N46E007" "N46E008" "N46E009" "N46E010" "N46E011" "N46E012" "N46E013" \
  "N47E006" "N47E007" "N47E008" "N47E009" "N47E010" "N47E011" "N47E012" "N47E013"

# Hawaii
process_area 0 $SRTM_BASE_3 "0_255" "0_1023" "0_4095" "0_2047" "2048_4095" \
  "N18W156" \
  "N19W155" "N19W156" "N19W157" \
  "N20W156" "N20W157" \
  "N21W157"

# Thailand - Khao Sok
process_area 0 $SRTM_BASE_3 "0_255" "0_1023" \
  "N08E098" "N09E098"

# Thailand - Chiang Mai
process_area 0 $SRTM_BASE_3 "0_1023" "0_2047" \
  "N18E098" "N18E099"
