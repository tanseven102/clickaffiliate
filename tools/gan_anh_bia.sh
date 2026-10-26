#!/usr/bin/env bash
# Chờ ảnh T-VIDEO (mã việc $1) vẽ xong → nén webp 1280x720 → assets/vi/bia-affiliate.webp → đẩy lên web
set -e
MA=$1; K=$(cat ~/.config/muse/api.key); cd "$(dirname "$0")/.."
for i in $(seq 1 360); do
  d=$(curl -s -m 10 http://127.0.0.1:8120/api/viec/$MA -H "X-API-Key: $K")
  ten=$(echo "$d" | python3 -c "import json,sys;r=json.load(sys.stdin)['ket_qua'][0];print(r.get('ten') or '' if r['trang_thai'] in ('xong','ok','done') else ('LOI:'+str(r.get('loi')) if r['trang_thai'] in ('loi','hong') else ''))")
  case "$ten" in LOI:*) echo "$ten"; exit 1;; "") sleep 30;; *) break;; esac
done
[ -z "$ten" ] && { echo "het gio cho anh"; exit 1; }
mkdir -p assets/vi
curl -s -m 60 "http://127.0.0.1:8120/api/anh/$ten" -H "X-API-Key: $K" -o /tmp/claude-1000/anh_bia_goc
python3 -c "
from PIL import Image; im=Image.open('/tmp/claude-1000/anh_bia_goc').convert('RGB')
w,h=im.size; t=16/9
im=im.crop(((w-int(h*t))//2,0,(w+int(h*t))//2,h)) if w/h>t else im.crop((0,(h-int(w/t))//2,w,(h+int(w/t))//2))
im.resize((1280,720),Image.LANCZOS).save('assets/vi/bia-affiliate.webp','WEBP',quality=82)"
git pull -q && git add assets/vi/bia-affiliate.webp && git commit -qm "Anh bia muc tieng Viet (T-VIDEO)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q && echo "DA GAN ANH $ten"
