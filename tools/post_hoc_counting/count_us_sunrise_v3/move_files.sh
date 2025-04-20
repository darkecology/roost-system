# Get tracks
mkdir predictions
for station in KTLX KCBW KCXX KGYX KTYX KBUF KENX KBGM KBOX KCCX KDIX KLWX KDOX KAKQ KRAX KMHX KLTX KOKX; do
  scp -r wenlongzhao@doppler.cs.umass.edu:/scratch2/wenlongzhao/roostui/data/us_sunrise_v3_bad_counts/tracks_${station}* predictions/
done

# Send tracks and per-sweep counts
#for station in KTLX KCBW KCXX KGYX KTYX KBUF KENX KBGM KBOX KCCX KDIX KLWX KDOX KAKQ KRAX KMHX KLTX KOKX; do
#  scp -r predictions/* wenlongzhao@doppler.cs.umass.edu:/scratch2/wenlongzhao/roostui/data/us_sunrise_v3/
#done