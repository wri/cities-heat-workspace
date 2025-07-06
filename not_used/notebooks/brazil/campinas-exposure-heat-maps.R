library(sf)
library(ggplot2)
library(leaflet)



###################################
# Heat spatial distribution map
###################################

# get heat data at the census tract level ----
heat_tract <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/heat_census.geojson")
heat_tract <- st_transform(heat_tract, crs = 4326)


# define palette for map
pal_heat_tract<- colorNumeric("RdYlBu", 
                              heat_tract$T_mean_mean_mean,
                              na.color = "transparent",
                              reverse = TRUE)


# define labels information for map
labels_heat_tract <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                            "Average surface temperature", heat_tract$T_mean_mean_mean,
                            "Max surface temperature", heat_tract$T_mean_mean_max
) %>% 
  lapply(htmltools::HTML)

# get heat data at the grid level  ----
heat_grid <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/campinas_heat.geojson")
heat_grid <- st_transform(heat_grid, crs = 4326)

# define palettes for map
pal_heat_grid<- colorNumeric("RdYlBu", 
                             heat_grid$T_mean_mea,
                              na.color = "transparent",
                              reverse = TRUE)


# define labels information for map
labels_heat_grid <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                             "Average surface temperature", heat_grid$T_mean_mea,
                             "Max surface temperature", heat_grid$T_mean_max
) %>% 
  lapply(htmltools::HTML)


# map plot of het data (grid + census tract level)

leaflet(heat_tract, height = 800, width = "100%")  %>%
  addTiles() %>%
  addProviderTiles(providers$OpenStreetMap, group = "OSM") %>%
  addProviderTiles(providers$CartoDB.DarkMatter, group = "CartoDB") %>%
  addProviderTiles(providers$Stamen.TonerLite, group = "Toner Lite") %>%
  # T_mean_mean_mean ----
addPolygons(data = heat_tract,
            group = "Surface temperature (tract)",
            fillColor = ~pal_heat_tract(T_mean_mean_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_tract,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_heat_tract,
            values = heat_tract$T_mean_mean_mean,
            opacity = 0.9,
            group = "Surface temperature (tract)",
            position = "topright",
            title = "Surface temperature (tract)",
            labFormat = labelFormat(suffix = "")) %>%
  # polygons ----
addPolygons(data = heat_grid,
            group = "Surface temperature",
            fillColor = ~pal_heat_grid(T_mean_mea),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend ----
addLegend(pal = pal_heat_grid,
          values = heat_grid$T_mean_mea,
          opacity = 0.9,
          group = "Surface temperature",
          position = "topright",
          labFormat = labelFormat(suffix = "")) %>%
  # Layers control 
  addLayersControl(
    baseGroups = c("OSM","Toner Lite", "CartoDB"),
    overlayGroups = c("Surface temperature (tract)",
                      "Surface temperature"),
    options = layersControlOptions(collapsed = FALSE)) %>%
  hideGroup(c("Surface temperature"))

###################################
# Socio-economic variables maps
###################################

# get census tract ----
census_tract <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/census_tract_prop.geojson")
census_tract <- st_transform(census_tract, crs = 4326)



# define palettes for maps
# variable: p_tot
pal_p_tot<- colorNumeric("RdYlBu", 
                         census_tract$p_tot,
                             na.color = "transparent",
                             reverse = TRUE)
# variable: propp_tot_f
pal_propp_tot_f<- colorNumeric("RdYlBu", 
                               census_tract$propp_tot_f,
                         na.color = "transparent",
                         reverse = TRUE)
# variable: propp_chddr
pal_propp_chddr<- colorNumeric("RdYlBu", 
                               census_tract$propp_chddr,
                               na.color = "transparent",
                               reverse = TRUE)
# variable: propp_indig
pal_propp_indig<- colorNumeric("RdYlBu", 
                               census_tract$propp_indig,
                               na.color = "transparent",
                               reverse = TRUE)

# define labels information
labels_p_tot <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                            "Total population", census_tract$p_tot,
                            "Percent female", census_tract$propp_tot_f
) %>% 
  lapply(htmltools::HTML)

# map plot

leaflet(exposure, height = 800, width = "100%")  %>%
  addTiles() %>%
  addProviderTiles(providers$OpenStreetMap, group = "OSM") %>%
  addProviderTiles(providers$CartoDB.DarkMatter, group = "CartoDB") %>%
  addProviderTiles(providers$Stamen.TonerLite, group = "Toner Lite") %>%
  # p_tot ----
  addPolygons(data = census_tract,
            group = "Total population",
            fillColor = ~pal_p_tot(p_tot),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_p_tot,
          values = census_tract$p_tot,
          opacity = 0.9,
          group = "Total popuation",
          position = "topright",
          title = "Total popuation <br> at the census tract level",
          labFormat = labelFormat(suffix = "")) %>%
  # prop_p_tot_f ----
addPolygons(data = census_tract,
            group = "Percent female",
            fillColor = ~pal_propp_tot_f(propp_tot_f),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_propp_tot_f,
            values = census_tract$propp_tot_f,
            opacity = 0.9,
            group = "Percent female",
            position = "topright",
            title = "Percent female",
            labFormat = labelFormat(suffix = "")) %>%
  # propp_chddr ----
addPolygons(data = census_tract,
            group = "Percent children (<14 y.o)",
            fillColor = ~pal_propp_chddr(propp_chddr),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_propp_chddr,
            values = census_tract$propp_chddr,
            opacity = 0.9,
            group = "Percent children (<14 y.o)",
            position = "topright",
            title = "Percent children (<14 y.o)",
            labFormat = labelFormat(suffix = "")) %>%
  # propp_indig ----
addPolygons(data = census_tract,
            group = "Percent elderly",
            fillColor = ~pal_propp_indig(propp_indig),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_propp_indig,
            values = census_tract$propp_indig,
            opacity = 0.9,
            group = "Percent indigenous",
            position = "topright",
            title = "Percent indigenous",
            labFormat = labelFormat(suffix = "")) %>%
  # Layers control 
  addLayersControl(
    baseGroups = c("OSM","Toner Lite", "CartoDB"),
    overlayGroups = c("Total popuation",
                      "Percent female",
                      "Percent children (<14 y.o)",
                      "Percent indigenous"),
    options = layersControlOptions(collapsed = FALSE)) %>%
    hideGroup(c("Percent female",
                "Percent children (<14 y.o)",
                "Percent indigenous"))

##################################
# exposure maps
##################################

exposure <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/exposure.geojson")
exposure <- st_transform(exposure, crs = 4326)


# define palettes for map
# palettes prop_p_0to14yr
pal_exposed_p_tot <- colorNumeric("RdYlBu", 
                                    exposure$p_tot,
                                    na.color = "grey",
                                    reverse = TRUE)

# palettes p_tot_f
pal_exposed_p_tot_f <- colorNumeric("RdYlBu", 
                         exposure$p_tot_f,
                         na.color = "transparent",
                         reverse = TRUE)

# palettes p_black
pal_exposed_p_black <- colorNumeric("RdYlBu", 
                                    exposure$p_black,
                                    na.color = "transparent",
                                    reverse = TRUE)

# palettes p_60.yr
pal_exposed_p_60 <- colorNumeric("RdYlBu", 
                                    exposure$p_60.yr,
                                    na.color = "transparent",
                                    reverse = TRUE)

# define labels information
labels_p_tot <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                        "Exposed population", exposure$p_tot,
                        "Exposed female", exposure$p_tot_f
) %>% 
  lapply(htmltools::HTML)

# map plot

leaflet(exposure, height = 700, width = "100%")  %>%
  addTiles() %>%
  addProviderTiles(providers$OpenStreetMap, group = "OSM") %>%
  addProviderTiles(providers$CartoDB.DarkMatter, group = "CartoDB") %>%
  addProviderTiles(providers$Stamen.TonerLite, group = "Toner Lite") %>%
  # polygons ----
addPolygons(data = heat_grid,
            group = "Surface temperature",
            fillColor = ~pal_heat_grid(T_mean_mea),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend ----
addLegend(pal = pal_heat_grid,
          values = heat_grid$T_mean_mea,
          opacity = 0.9,
          group = "Surface temperature",
          position = "topright",
          labFormat = labelFormat(suffix = "")) %>%
  # p_tot ----
addPolygons(data = exposure,
            group = "Exposed population",
            fillColor = ~pal_exposed_p_tot(p_tot),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_exposed_p_tot,
            values = exposure$p_tot,
            opacity = 0.9,
            group = "Exposed population",
            position = "topright",
            title = "Exposed population",
            labFormat = labelFormat(suffix = "")) %>%
  # p_tot_f ----
addPolygons(data = exposure,
            group = "Exposed female",
            fillColor = ~pal_exposed_p_tot_f(p_tot_f),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_exposed_p_tot_f,
            values = exposure$p_tot_f,
            opacity = 0.9,
            group = "Exposed female",
            position = "topright",
            title = "Exposed female",
            labFormat = labelFormat(suffix = "")) %>%
  # p_black ----
addPolygons(data = exposure,
            group = "Exposed black",
            fillColor = ~pal_exposed_p_black(p_black),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_exposed_p_black,
            values = exposure$p_black,
            opacity = 0.9,
            group = "Exposed black",
            position = "topright",
            title = "Exposed black",
            labFormat = labelFormat(suffix = "")) %>%
  # p_black ----
addPolygons(data = exposure,
            group = "Exposed elderly",
            fillColor = ~pal_exposed_p_60(p_60.yr),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_p_tot,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_exposed_p_60,
            values = exposure$p_60.yr,
            opacity = 0.9,
            group = "Exposed elderly",
            position = "topright",
            title = "Exposed elderly",
            labFormat = labelFormat(suffix = "")) %>%
  # Layers control 
  addLayersControl(
    baseGroups = c("OSM","Toner Lite", "CartoDB"),
    overlayGroups = c("Exposed population",
                      "Exposed female",
                      "Exposed black",
                      "Exposed elderly",
                      "Surface temperature"),
    options = layersControlOptions(collapsed = FALSE)) %>%
  hideGroup(c("Exposed female",
              "Exposed black",
              "Exposed elderly",
              "Surface temperature"))

