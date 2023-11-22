library(sf)
library(ggplot2)
library(leaflet)



###################################
# Tract and Grid spatial distribution maps - Hazard
###################################

# get hazard data at the census tract level ----
all_hazard <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/all_hazard_tract.geojson")
all_hazard <- st_transform(all_hazard, crs = 4326)


  # define palette for surface temperature (tract) ----
  pal_heat_mean <- colorNumeric("RdYlBu", 
                                all_hazard$Heat_T_mean_mean_mean,
                                na.color = "transparent",
                                reverse = TRUE)
  
  
  # define labels information for map
  labels_heat_mean <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                               "Average Surface Temperature", all_hazard$Heat_T_mean_mean_mean,
                               "Max Surface Temperature", all_hazard$Heat_T_mean_mean_max
  ) %>% 
    lapply(htmltools::HTML)
  
  
  # define palette for heat risk index (tract) ----
  pal_heat_risk_mean <- colorNumeric("RdYlBu", 
                               all_hazard$Heat_risco_indi_mean,
                               na.color = "transparent",
                               reverse = TRUE)
  
  
  # define labels information for map
  labels_heat_risk_mean <- sprintf("<strong>%s</strong> %s",# <br/><strong>%s:</strong> %s",
                              "Average Heat Risk Index", all_hazard$Heat_risco_indi_mean#,
                              #"Max Heat Risk Index", all_hazard$Heat_risco_indi_max
  ) %>% 
    lapply(htmltools::HTML)
  
  
  
  # define palette for landslide index (tract) ----
  pal_landslide_mean<- colorNumeric("RdYlBu", 
                               all_hazard$Landslide_indice_sum_mean,
                               na.color = "transparent",
                               reverse = TRUE)
  
  
  # define labels information for map
  labels_landslide_mean <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                              "Average Landslide Index", all_hazard$Landslide_indice_sum_mean,
                              "Max Landslide Index", all_hazard$Landslide_indice_sum_max
  ) %>% 
    lapply(htmltools::HTML)
  
  # define palette for flood index (tract) ----
  pal_flood_mean<- colorNumeric("RdYlBu", 
                                    all_hazard$Flood_indice_sum_mean,
                                    na.color = "transparent",
                                    reverse = TRUE)
  
  
  # define labels information for map
  labels_flood_mean <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                                   "Average Flood Index", all_hazard$Flood_indice_sum_mean,
                                   "Max Flood Index", all_hazard$Flood_indice_sum_max
  ) %>% 
    lapply(htmltools::HTML)
  
  # define palette for inundation index (tract) ----
  pal_inundation_mean<- colorNumeric("RdYlBu", 
                                    all_hazard$Inundation_indice_sum_mean,
                                    na.color = "transparent",
                                    reverse = TRUE)
  
  
  # define labels information for map
  labels_inundation_mean <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                                   "Average Inundation Index", all_hazard$Inundation_indice_sum_mean,
                                   "Max Inundation Index", all_hazard$Inundation_indice_sum_max
  ) %>% 
    lapply(htmltools::HTML)
  
  
# get hazard data at the grid level  ----
hazard_grid <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/all_hazard_grid.geojson")
hazard_grid <- st_transform(hazard_grid, crs = 4326)

  # define palettes for surface temperature grid ----
  pal_heat_grid<- colorNumeric("RdYlBu", 
                               hazard_grid$heat_T_mean_mea,
                               na.color = "transparent",
                               reverse = TRUE)
  
  
  # define labels information for map
  labels_heat_grid <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                              "Average Surface Temperature", hazard_grid$heat_T_mean_mea,
                              "Max Surface Temperature", hazard_grid$heat_T_mean_max
  ) %>% 
    lapply(htmltools::HTML)
  
  # define palettes for heat risk grid ----
pal_heat_risk_grid<- colorNumeric("RdYlBu", 
                                  hazard_grid$heat_risco_indi,
                             na.color = "transparent",
                             reverse = TRUE)


# define labels information for map
labels_heat_risk_grid <- sprintf("<strong>%s</strong> %s <br/><strong>%s:</strong> %s",
                            "Heat Risk Index", hazard_grid$heat_risco_indi,
                            "Heat Vulnerability Index", hazard_grid$heat_vuln_indic
) %>% 
  lapply(htmltools::HTML)


  # define palettes for landslide grid ----
pal_landslide_grid<- colorNumeric("RdYlBu",
                                  hazard_grid$landslide_indice_sum,
                             na.color = "transparent",
                             reverse = TRUE)


# define labels information for map
labels_landslide_grid <- sprintf("<strong>%s</strong> %s",# %s <br/><strong>%s:</strong> %s",
                            "Average Lanslide Index ", hazard_grid$landslide_indice_sum
) %>% 
  lapply(htmltools::HTML)



  # define palettes for flood grid ----
pal_flood_grid<- colorNumeric("RdYlBu",
                              hazard_grid$flood_indice_sum,
                                  na.color = "transparent",
                                  reverse = TRUE)


# define labels information for map
labels_flood_grid <- sprintf("<strong>%s</strong> %s",# %s <br/><strong>%s:</strong> %s",
                                 "Average Flood Index ", hazard_grid$flood_indice_sum
) %>% 
  lapply(htmltools::HTML)




  # define palettes for inundation grid ----
pal_inundation_grid<- colorNumeric("RdYlBu",
                                   hazard_grid$inundation_indice_sum,
                              na.color = "transparent",
                              reverse = TRUE)


# define labels information for map
labels_inundation_grid <- sprintf("<strong>%s</strong> %s",# %s <br/><strong>%s:</strong> %s",
                             "Average Inundation Index ", hazard_grid$inundation_indice_sum
) %>% 
  lapply(htmltools::HTML)



# map plot of hazard data (grid + census tract level) ----

leaflet(all_hazard, height = 800, width = "100%")  %>%
  addTiles() %>%
  addProviderTiles(providers$OpenStreetMap, group = "OSM") %>%
  addProviderTiles(providers$CartoDB.DarkMatter, group = "CartoDB") %>%
  addProviderTiles(providers$Stadia.StamenTonerLite, group = "Toner Lite") %>%

  # Heat T_mean_mean_mean ----
addPolygons(data = all_hazard,
            group = "Surface Temperature (tract)",
            fillColor = ~pal_heat_mean(Heat_T_mean_mean_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_mean,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
addLegend(pal = pal_heat_mean,
            values = all_hazard$Heat_T_mean_mean_mean,
            opacity = 0.9,
            group = "Surface Temperature (tract)",
            position = "topright",
            title = "Surface Temperature in °C (tract)",
            labFormat = labelFormat(suffix = "")) %>%

  # Heat risk index ----
addPolygons(data = all_hazard,
            group = "Heat Risk Index (tract)",
            fillColor = ~pal_heat_risk_mean(Heat_risco_indi_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_risk_mean,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_heat_risk_mean,
            values = all_hazard$Heat_risco_indi_mean,
            opacity = 0.9,
            group = "Heat Risk Index (tract)",
            position = "topright",
            title = "Heat Risk Index (tract)",
            labFormat = labelFormat(suffix = "")) %>%
  
  # Landslide_indice_sum_mean ----
addPolygons(data = all_hazard,
            group = "Landslide Index (tract)",
            fillColor = ~pal_landslide_mean(Landslide_indice_sum_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_landslide_mean,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_landslide_mean,
            values = all_hazard$Landslide_indice_sum_mean,
            opacity = 0.9,
            group = "Landslide Index (tract)",
            position = "topright",
            title = "Landslide Index (tract)",
            labFormat = labelFormat(suffix = "")) %>%

  # Flood_indice_sum_mean ----
addPolygons(data = all_hazard,
            group = "Flood Index (tract)",
            fillColor = ~pal_flood_mean(Flood_indice_sum_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_flood_mean,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_flood_mean,
            values = all_hazard$Flood_indice_sum_mean,
            opacity = 0.9,
            group = "Flood Index (tract)",
            position = "topright",
            title = "Flood Index (tract)",
            labFormat = labelFormat(suffix = "")) %>%

  # Inundation_indice_sum_mean ----
addPolygons(data = all_hazard,
            group = "Inundation Index (tract)",
            fillColor = ~pal_inundation_mean(Inundation_indice_sum_mean),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_inundation_mean,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend 
  addLegend(pal = pal_inundation_mean,
            values = all_hazard$Inundation_indice_sum_mean,
            opacity = 0.9,
            group = "Inundation Index (tract)",
            position = "topright",
            title = "Inundation Index (tract)",
            labFormat = labelFormat(suffix = "")) %>%
  
  
  # Heat grid Surface Temperature ----
addPolygons(data = hazard_grid,
            group = "Surface Temperature (grid)",
            fillColor = ~pal_heat_grid(heat_T_mean_mea),
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
  # legend
addLegend(pal = pal_heat_grid,
          values = hazard_grid$heat_T_mean_mea,
          opacity = 0.9,
          group = "Surface Temperature (grid)",
          position = "topright",
          title = "Surface Temperature in °C (grid)",
          labFormat = labelFormat(suffix = "")) %>%
  
  # Heat grid Risk ----
addPolygons(data = hazard_grid,
            group = "Heat Risk Index (grid)",
            fillColor = ~pal_heat_risk_grid(heat_risco_indi),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_heat_risk_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_heat_risk_grid,
            values = hazard_grid$heat_risco_indi,
            opacity = 0.9,
            group = "Heat Risk Index (grid)",
            position = "topright",
            title = "Heat Risk Index (grid)",
            labFormat = labelFormat(suffix = "")) %>%
  
  # Landslide grid ----
addPolygons(data = hazard_grid,
            group = "Landslide Index (grid)",
            fillColor = ~pal_landslide_grid(landslide_indice_sum),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_landslide_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_landslide_grid,
            values = hazard_grid$landslide_indice_sum,
            opacity = 0.9,
            group = "Landslide Index (grid)",
            position = "topright",
            title = "Landslide Index (grid)",
            labFormat = labelFormat(suffix = "")) %>%
  
  # Flood grid ----
addPolygons(data = hazard_grid,
            group = "Flood Index (grid)",
            fillColor = ~pal_flood_grid(flood_indice_sum),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_flood_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_flood_grid,
            values = hazard_grid$flood_indice_sum,
            opacity = 0.9,
            group = "Flood Index (grid)",
            position = "topright",
            title = "Flood Index (grid)",
            labFormat = labelFormat(suffix = "")) %>%
  
  # Inundation grid ----
addPolygons(data = hazard_grid,
            group = "Inundation Index (grid)",
            fillColor = ~pal_inundation_grid(inundation_indice_sum),
            weight = 0.1,
            opacity = 1,
            color = "grey",
            fillOpacity = 0.9,
            label = labels_inundation_grid,
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"),
              textsize = "15px",
              direction = "auto")) %>%
  # legend
  addLegend(pal = pal_inundation_grid,
            values = hazard_grid$inundation_indice_sum,
            opacity = 0.9,
            group = "Inundation Index (grid)",
            position = "topright",
            title = "Inundation Index (grid)",
            labFormat = labelFormat(suffix = "")) %>%
  
  # Layers control ---- 
  addLayersControl(
    baseGroups = c("OSM", "CartoDB","Toner Lite"),#,"Toner Lite"
    overlayGroups = c("Surface Temperature (tract)", "Heat Risk Index (tract)",
                      "Landslide Index (tract)", "Flood Index (tract)", "Inundation Index (tract)",
                      "Surface Temperature (grid)", "Heat Risk Index (grid)", "Landslide Index (grid)",
                      "Flood Index (grid)", "Inundation Index (grid)"),
    options = layersControlOptions(collapsed = FALSE)) %>%
  hideGroup(c("Heat Risk Index (tract)", "Landslide Index (tract)", "Flood Index (tract)", "Inundation Index (tract)",
              "Surface Temperature (grid)", "Heat Risk Index (grid)", "Landslide Index (grid)",
              "Flood Index (grid)", "Inundation Index (grid)"))
