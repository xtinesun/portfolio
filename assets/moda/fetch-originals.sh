#!/bin/bash
# Downloads the original, full-resolution Moda Operandi case-study images from UXfolio
# into assets/moda/src/. Run once:  bash ~/Desktop/Christine/Cursor/assets/moda/fetch-originals.sh
set -e
cd "$(dirname "$0")"
mkdir -p src
A=https://uxfolio-prod.s3.us-east-1.amazonaws.com/5c953a66c9821a0004a139eb/5e3711c6cf2a9b0004ea3ecf
P=https://uxfolio-prod.s3.us-east-1.amazonaws.com/5c953a66c9821a0004a139eb/5c953cccc9821a0004a139ec
get() { echo "  $2"; curl -fsSL "$1" -o "src/$2"; }
echo "Downloading Added to Cart images..."
get $A/PJRU3sJcGdjL8hL1.png cart-audit-1.png
get $A/1mn9zcmUGnk0DtKS.png cart-audit-2.png
get $A/oOltzoGGRrVyRV0A.png cart-audit-3.png
get $A/oHi9tz4iYERURoss.jpg cart-competitive.jpg
get $A/vPhvl9iHne3FbdqG.jpg cart-flows.jpg
get $A/5vywrBWaKBExGqbX.png cart-design-2.png
get $A/t7RxNeo5HdfygOLH.png cart-design-3.png
get $A/BAUgVn6eWPs8Cx6k.png cart-design-4.png
get $A/nYVEgR2C1gDcGTIY.png cart-bag-options.png
get $A/0KNLbvyPK3dZt7iv.jpg cart-final-bag.jpg
echo "Downloading Personalization images..."
get $P/ON1Yyy0ict7F0DVZ.jpg pers-hero.jpg
get $P/i1d2H8D7mKhQOy06.jpg pers-agenda.jpg
get $P/xCmQGgKci2UkVIdE.jpg pers-hmw.jpg
get $P/jrRXDJeouZtP8YEF.jpg pers-journey.jpg
get $P/am9wdF1oEo9JKqyq.jpg pers-lightning.jpg
get $P/tgOveXeTeTDinOKu.png pers-art-museum.png
get $P/O70tn0kpbMCVxnIg.JPG pers-test-flow.jpg
get $P/5AE7OO2WHvaQTvxK.png pers-plp-prototype.png
get $P/ywGcCYN6rMMmZ7nw.png pers-pdp-prototype.png
echo "Done: $(ls src | wc -l | tr -d ' ') images in assets/moda/src"
