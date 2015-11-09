# Show tracks
library(leaflet)

tracks <- read.csv("~/Google Drive/Raspberry Pi/noise-monitor/dump1090/tracks.csv")

base_map = leaflet() %>% 
  addTiles(urlTemplate='https://{s}.tiles.mapbox.com/v3/kent37.npinlfln/{z}/{x}/{y}.png',
           attribution='<a href="http://www.mapbox.com/about/maps/" target="_blank">Terms &amp; Feedback</a>') %>% 
  setView(-71.098636, 42.412736, zoom = 10)

base_map %>% addCircles(tracks$lon, tracks$lat)
