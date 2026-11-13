#!/bin/bash
# Host side: one dry-run box in a private mount namespace (overlay over /, writes land in sb/<box>/up; the host is
# not changed), then chroot and run inner.sh. Usage: box.sh BOX RUN_ID COMMIT
BOX=$1; RUN_ID=$2; COMMIT=$3
GA=/tmp/claude-0/-home-user-v2d-track3/c39cfb04-cc2f-58cd-b84d-df803d82b152/scratchpad/gA; SB=$GA/sb/$BOX
rm -rf $SB $GA/out/$BOX; mkdir -p $SB/up $SB/wk $SB/m $GA/out/$BOX
unshare -m --propagation private bash -c "
set -e
mount -t overlay overlay -o lowerdir=/,upperdir=$SB/up,workdir=$SB/wk $SB/m
for d in proc sys dev; do mount --rbind /\$d $SB/m/\$d; done
mount --bind $GA/out/$BOX $SB/m$GA/out/$BOX
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root TERM=dumb \
  HTTPS_PROXY=\$HTTPS_PROXY https_proxy=\$https_proxy NO_PROXY=\$NO_PROXY no_proxy=\$no_proxy \
  SSL_CERT_FILE=\$SSL_CERT_FILE REQUESTS_CA_BUNDLE=\$REQUESTS_CA_BUNDLE CURL_CA_BUNDLE=\$CURL_CA_BUNDLE \
  PIP_CERT=\$PIP_CERT GIT_SSL_CAINFO=\$SSL_CERT_FILE \
  chroot $SB/m /bin/bash $GA/dry/inner.sh $BOX $RUN_ID $COMMIT $GA
"
