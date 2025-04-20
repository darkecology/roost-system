#!/bin/bash
hostname
SPECIES=$1
STATION=$2
START=$3
YEAR=${START:0:4}
END=$4
SUN_ACTIVITY=$5
MIN_BEFORE=$6
MIN_AFTER=$7
OUTPUT_ROOT=$8
MODEL_NAME=$9  # we deploy this model and get annotations from this model

DST_HOST=${10}
DST_IMG=${11}
DST_PRED=${12}
DST_OTHERS=${13}

python 1_deploy.py \
--species ${SPECIES} --station ${STATION} --start ${START} --end ${END} \
--sun_activity ${SUN_ACTIVITY} --min_before ${MIN_BEFORE} --min_after ${MIN_AFTER} \
--model_name ${MODEL_NAME} --data_root ${OUTPUT_ROOT}/${MODEL_NAME} --keep_scans

##### Transfer outputs. Only transfer the currently processed station-year. #####
# Transfer outputs for the UI in the verbose mode and with compression
# (1) images to visualize dz05 and vr05  TODO: remove
PATTERN="*/${YEAR}/*/*/${STATION}/*"  # ${} will be expanded, * remains as is
echo "##### Transferring images: $PATTERN #####"
ssh ${DST_HOST} mkdir -p ${DST_IMG}/${MODEL_NAME}
rsync --remove-source-files -avz \
--include='*/' \
--include="$PATTERN" \
--exclude='*' \
${OUTPUT_ROOT}/${MODEL_NAME}/ui/img/ \
${DST_HOST}:${DST_IMG}/${MODEL_NAME}/

# (2) bounding boxes and counts  TODO: also move to counting-labels
PATTERN="*${STATION}_${YEAR}*"
echo "##### Transferring detections: $PATTERN #####"
ssh ${DST_HOST} mkdir -p ${DST_PRED}/${MODEL_NAME}
rsync --remove-source-files -avz \
--include="$PATTERN" \
--exclude='*' \
${OUTPUT_ROOT}/${MODEL_NAME}/ui/scans_and_tracks/ \
${DST_HOST}:${DST_PRED}/${MODEL_NAME}/

# (4) logs  TODO: move to counting-labels
PATTERN="${STATION}/${YEAR}/*"
echo "##### Transferring logs: $PATTERN #####"
ssh ${DST_HOST} mkdir -p ${DST_OTHERS}/${MODEL_NAME}/logs
rsync --remove-source-files -av \
--include="${STATION}/" \
--include="${STATION}/${YEAR}/" \
--include="$PATTERN" \
--exclude='*' \
${OUTPUT_ROOT}/${MODEL_NAME}/logs/ \
${DST_HOST}:${DST_OTHERS}/${MODEL_NAME}/logs/
