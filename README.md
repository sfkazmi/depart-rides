# Depart Rides — Complete Static Website

Open `index.html` in a modern browser or serve the folder with `python -m http.server 8000`.

## Pages
Home, Fleet, Vehicle Detail (dynamic query parameter), Booking Inquiry, About, FAQ, Contact, Rental Terms, Privacy.

## Actual fleet
Toyota Prado, Haval H6, Jetour T2, Toyota Corolla XLi 2015 (black), Toyota Land Cruiser V8 2018.

## Images
The four Land Cruiser V8 photographs in `assets/` are real images provided by the business. Images for other vehicles are third-party illustrative placeholders and require an internet connection. Replace them with actual vehicle images before launch.

## Forms
Booking and contact forms are functional client-side validation and create an email draft in the visitor's default email app. They DO NOT transmit data, create confirmed bookings, check live availability or take payments. A production deployment needs business contact details, backend or form service, privacy and legal review, real rental pricing and terms.

## Animation
Hero zoom, kinetic headline, parallax scroll, reveal-on-scroll, staggered cards, hover lifts, moving marquee, sticky navigation. `prefers-reduced-motion` is respected.

## Customization
Edit fleet details in `assets/app.js` under `CARS`, and visual styles in `assets/style.css`.

## Newly provided media
- Toyota Prado: three actual photos in assets/prado-*.jpg, included in its vehicle gallery.
- Additional GWM vehicle video: assets/fleet-gwm-video.mp4. Model not independently verified; preserved for review before associating with a particular listing.
