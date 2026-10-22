# Depart Rides — Complete Static Website

Open `index.html` in a modern browser or serve the folder with `python -m http.server 8000`.

Live: https://sfkazmi.github.io/depart-rides/

## Pages
Home, Fleet, Vehicle Detail (dynamic query parameter), Booking Inquiry, About, FAQ, Contact, Rental Terms, Privacy.

## Actual fleet
Toyota Prado, Haval H6, Jetour T2, Toyota Corolla XLi 2015 (black), Toyota Land Cruiser V8 2018.

## Pricing
No numeric rental rates exist in the original site data. Every vehicle is labelled **On request** (the copy already used on fleet and vehicle pages). The cinematic home “pricing” strip uses that same label — it does not invent prices.

Performance counters on the home sequence use facts already on the site: 5 fleet vehicles, Prado 7 seats, 24/7 inquiry, 2018 flagship V8 year.

## Images
The Land Cruiser V8 and Prado photographs in `assets/` are real images provided by the business. Images for other vehicles are third-party illustrative placeholders and require an internet connection. Replace them with actual vehicle images before launch.

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
| `assets/stock-engine-alt.jpg` | [Pexels](https://www.pexels.com/photo/190574/) | chrome engine close-up |

Unsplash License / Pexels License: free to use, with photographer credit.

## Forms
Booking and contact forms are functional client-side validation and create an email draft in the visitor's default email app. They DO NOT transmit data, create confirmed bookings, check live availability or take payments. A production deployment needs business contact details, backend or form service, privacy and legal review, real rental pricing and terms.

## Animation
The home page is a pinned, scroll-driven cinematic sequence (GSAP + ScrollTrigger via jsDelivr CDN): the Land Cruiser drives into frame, the camera zooms into an interior, then pulls back to the front/engine with animated counters and on-request pricing, then fleet, motion reel, booking CTA and footer. Other pages share the dark luxury palette, serif display type, and reveal-on-scroll. `prefers-reduced-motion` disables pin/tween and shows stacked static scenes. No build step.

## Customization
Edit fleet details in `assets/app.js` under `CARS`, cinematic motion in `assets/cinematic.js`, and visual styles in `assets/style.css`.

## Newly provided media
- Toyota Prado: three actual photos in assets/prado-*.jpg, included in its vehicle gallery.
- Additional GWM vehicle video: assets/fleet-gwm-video.mp4. Model not independently verified; used as a motion reel on the home page.
