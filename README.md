# Depart Rides — Complete Static Website

Open `index.html` in a modern browser or serve the folder with `python -m http.server 8000`.

Live: https://sfkazmi.github.io/depart-rides/

## Pages
Home, Fleet, Vehicle Detail (dynamic query parameter), Booking Inquiry, About, FAQ, Contact, Rental Terms, Privacy.

## Actual fleet
Toyota Prado 2024, Haval H6 2025, Jetour T2 2026, Toyota Corolla XLi 2014 (black), Toyota Land Cruiser V8 2018.

## Pricing
No numeric rental rates exist in the original site data. Every vehicle is labelled **On request** (the copy already used on fleet and vehicle pages). The cinematic home “pricing” strip uses that same label — it does not invent prices.

Performance counters on the home sequence use facts already on the site: 5 fleet vehicles, Prado 7 seats, 24/7 inquiry, 2018 flagship V8 year.

## Images
The Land Cruiser V8 and Prado photographs in `assets/` are real images provided by the business. Haval H6, Jetour T2 and Corolla XLi images are freely licensed illustrative photos of each model from Wikimedia Commons (see credits below), stored locally in `assets/`. Replace them with photos of the actual cars when available.

### Stock interior and engine stills
Cabin and engine photography of the actual fleet does not exist in `assets/`. The home sequence uses downloaded, free-license stills (illustrative only — not Depart Rides vehicles):

| File | Source | Credit |
| --- | --- | --- |
| `assets/stock-cabin.jpg` | [Unsplash](https://unsplash.com/photos/nmI1lNdv_jg) | Bram Van Oost (`@ort`) — Hongqi E-HS9 cabin |
| `assets/stock-seats.jpg` | [Unsplash](https://unsplash.com/photos/aKTAKvDnPcc) | Vadym Kudriavtsev (`@clipnjoy`) — quilted leather seat |
| `assets/stock-interior.jpg` | [Unsplash](https://unsplash.com/photos/JFZNAg-elAI) | Titi Iaru (`@titi_iaru`) — Aston Martin cabin |
| `assets/stock-leather.jpg` | [Unsplash](https://unsplash.com/photos/gXaWrl4eQ0c) | Christopher Lam (`@cwdlphotos`) — Porsche cabin |
| `assets/stock-wheel.jpg` | [Unsplash](https://unsplash.com/photos/FZcQRwFSR1Y) | Leiada Krözjhen (`@leiadakrozjhen`) — tan luxury cabin |
| `assets/stock-engine.jpg` | [Unsplash](https://unsplash.com/photos/D4YRzVtynV8) | engine bay still (`photo-1486262715619-67b85e0b08d3`) |

Unsplash License / Pexels License: free to use, with photographer credit.

## Forms
Booking and contact forms are functional client-side validation and create an email draft in the visitor's default email app. They DO NOT transmit data, create confirmed bookings, check live availability or take payments. A production deployment needs business contact details, backend or form service, privacy and legal review, real rental pricing and terms.

## Animation
The home page is a pinned, scroll-driven cinematic sequence (GSAP + ScrollTrigger via jsDelivr CDN): the Land Cruiser drives into frame, the camera zooms into an interior, then pulls back to the front/engine with animated counters and on-request pricing, then fleet, motion reel, booking CTA and footer. Other pages share the dark luxury palette, serif display type, and reveal-on-scroll. `prefers-reduced-motion` disables pin/tween and shows stacked static scenes. No build step.

## Customization
Edit fleet details in `assets/app.js` under `CARS`, cinematic motion in `assets/cinematic.js`, and visual styles in `assets/style.css`.

## Newly provided media
- Haval H6: owner-supplied studio rear photo `assets/haval-h6-rear.jpg` (in its gallery and the reel).
- Toyota Prado: three actual photos in assets/prado-*.jpg, included in its vehicle gallery.
- Home page motion reel: `assets/fleet-reel.mp4` (+ `fleet-reel-poster.jpg`), built with ffmpeg (Ken Burns zooms/pans, crossfades) from the business's own studio photos `land-cruiser-*`, `prado-*`, `v8-*` and `haval-h6-rear.jpg`. 1920x1080, ~20s, H.264, no audio. Replaces the former GWM video, which was removed because it showed bystanders.

## Wikimedia Commons photo credits
Shown on the site (fleet page note and each vehicle page). Images were resized/cropped; the Jetour front photo has background bystanders blurred.

| File | Source | Author | License |
|---|---|---|---|
| `assets/haval-h6-front.jpg` | [File:Haval_H6_III_007.jpg](https://commons.wikimedia.org/wiki/File:Haval_H6_III_007.jpg) | Jengtingchen | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `assets/jetour-t2-front.jpg` | [File:Jetour_Traveller_001.jpg](https://commons.wikimedia.org/wiki/File:Jetour_Traveller_001.jpg) | JustAnotherCarDesigner | CC BY-SA 4.0 |
| `assets/jetour-t2-rear.jpg` | [File:Jetour_Traveller_006.jpg](https://commons.wikimedia.org/wiki/File:Jetour_Traveller_006.jpg) | JustAnotherCarDesigner | CC0 |
| `assets/jetour-t2-side.jpg` | [File:Jetour_Traveller_012.jpg](https://commons.wikimedia.org/wiki/File:Jetour_Traveller_012.jpg) | JustAnotherCarDesigner | CC0 |
| `assets/corolla-xli-front.jpg` | [File:Toyota_Altis_2.0_V_(Attitude_Black).jpg](https://commons.wikimedia.org/wiki/File:Toyota_Altis_2.0_V_(Attitude_Black).jpg) | Captainmorlypogi1959 | CC BY-SA 4.0 |
