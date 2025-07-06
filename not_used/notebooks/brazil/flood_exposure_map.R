library(sf)
library(ggplot2)
library(leaflet)




###################################
# Spatial distribution maps - Census Tract Variables - For Exposed Areas
###################################

# get hazard data at the census tract level ----
census_tract <- st_read("https://cities-socio-economic-vulnerability.s3.eu-west-3.amazonaws.com/case-studies/campinas/maps/flood_exposed75_tract.geojson")
census_tract <- st_transform(census_tract, crs = 4326)


# define palette for p_tot ----
pal_p_tot <- colorNumeric("RdYlBu", 
                          census_tract$p_tot, #change
                          na.color = "grey",
                          reverse = TRUE)


# define labels information for map
labels_p_tot <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                        "Total Population", census_tract$p_tot, #change
                        "Percentage of Population", census_tract$prop2_p_tot #change
) %>% 
  lapply(htmltools::HTML)

# define palette for hazard ----
pal_hazard <- colorNumeric("RdYlBu", 
                           census_tract$Flood_indice_sum_mean, #change
                           na.color = "grey",
                           reverse = TRUE)


# define labels information for map
labels_hazard <- sprintf("<strong>%s:</strong> %s ", #change
                         "Average Flood Risk Index", round(census_tract$Flood_indice_sum_mean,3)
) %>% 
  lapply(htmltools::HTML)

# define palette for p_tot_f ----
pal_p_tot_f <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_tot_f, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_tot_f <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Female Population", census_tract$p_tot_f, #change
                          "Share of Female Population in Tract", census_tract$prop1_p_tot_f, #change
                          "Share in Total Female Population of City", census_tract$prop2_p_tot_f #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_tot_m ----
pal_p_tot_m <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_tot_m, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_tot_m <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Male Population", census_tract$p_tot_m, #change
                          "Share of Male Population in Tract", census_tract$prop1_p_tot_m, #change
                          "Share in Total Male Population of City", census_tract$prop2_p_tot_m #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_wht ----
pal_p_wht <- colorNumeric("RdYlBu", 
                          census_tract$prop1_p_wht, #change
                          na.color = "grey",
                          reverse = TRUE)


# define labels information for map
labels_p_wht <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                        "Total White Population", census_tract$p_wht, #change
                        "Share of White Population in Tract", census_tract$prop1_p_wht, #change
                        "Share in Total White Population of City", census_tract$prop2_p_wht #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_black ----
pal_p_black <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_black, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_black <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Black Population", census_tract$p_black, #change
                          "Share of Black Population in Tract", census_tract$prop1_p_black, #change
                          "Share in Total Black Population of City", census_tract$prop2_p_black #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_yellow ----
pal_p_yellow <- colorNumeric("RdYlBu", 
                             census_tract$prop1_p_yellow, #change
                             na.color = "grey",
                             reverse = TRUE)


# define labels information for map
labels_p_yellow <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                           "Total Yellow Population", census_tract$p_yellow, #change
                           "Share of Yellow Population in Tract", census_tract$prop1_p_yellow, #change
                           "Share in Total Yellow Population of City", census_tract$prop2_p_yellow #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_brown ----
pal_p_brown <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_brown, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_brown <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Brown Population", census_tract$p_brown, #change
                          "Share of Brown Population in Tract", census_tract$prop1_p_brown, #change
                          "Share in Total Brown Population of City", census_tract$prop2_p_brown #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_indig ----
pal_p_indig <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_indig, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_indig <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Brown Population", census_tract$p_indig, #change
                          "Share of Brown Population in Tract", census_tract$prop1_p_indig, #change
                          "Share in Total Brown Population of City", census_tract$prop2_p_indig #change
) %>% 
  lapply(htmltools::HTML) 

# define palette for p_0to14yr ----
pal_p_0to14yr <- colorNumeric("RdYlBu", 
                              census_tract$prop1_p_0to14yr, #change
                              na.color = "grey",
                              reverse = TRUE)


# define labels information for map
labels_p_0to14yr <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                            "Total Population with Age Lesser than 14", census_tract$p_0to14yr, #change
                            "Share of Population with Age Lesser than 14 in Tract", census_tract$prop1_p_0to14yr, #change
                            "Share in Total Population of City with Age Lesser than 14", census_tract$prop2_p_0to14yr #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_15to19yr ----
pal_p_15to19yr <- colorNumeric("RdYlBu", 
                               census_tract$prop1_p_15to19yr, #change
                               na.color = "grey",
                               reverse = TRUE)


# define labels information for map
labels_p_15to19yr <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                             "Total Population with Age Between 15 and 19", census_tract$p_15to19yr, #change
                             "Share of Population with Age Between 15 and 19 in Tract", census_tract$prop1_p_15to19yr, #change
                             "Share in Total Population of City with Age Between 15 and 19", census_tract$prop2_p_15to19yr #change
) %>% 
  lapply(htmltools::HTML)

# define palette for p_20to59yr ----
pal_p_20to59yr <- colorNumeric("RdYlBu", 
                               census_tract$prop1_p_20to59yr, #change
                               na.color = "grey",
                               reverse = TRUE)


# define labels information for map
labels_p_20to59yr <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                             "Total Population with Age Between 20 and 59", census_tract$p_20to59yr, #change
                             "Share of Population with Age Between 20 and 59 in Tract", census_tract$prop1_p_20to59yr, #change
                             "Share in Total Population of City with Age Between 20 and 59", census_tract$prop2_p_20to59yr #change
) %>% 
  lapply(htmltools::HTML) 


# define palette for p_60+yr ----
pal_p_60.yr <- colorNumeric("RdYlBu", 
                            census_tract$prop1_p_60.yr, #change
                            na.color = "grey",
                            reverse = TRUE)


# define labels information for map
labels_p_60.yr <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                          "Total Population with Age Above 60", census_tract$p_60.yr, #change
                          "Share of Population with Age Above 60 in Tract", census_tract$prop1_p_60.yr, #change
                          "Share in Total Population of City with Age Above 60", census_tract$prop2_p_60.yr #change
) %>% 
  lapply(htmltools::HTML)


# define palette for p_mean_inc1 ----
pal_p_mean_inc1 <- colorNumeric("RdYlBu", 
                                census_tract$p_mean_inc1, #change
                                na.color = "grey",
                                reverse = TRUE)


# define labels information for map
labels_p_mean_inc1 <- sprintf("<strong>%s:</strong> %s <br/><strong>%s:</strong> %s", #change
                              "Average Income in Tract", census_tract$p_mean_inc1, #change
                              "Percentage of Income compared to City Average", census_tract$prop2_p_mean_inc1 #change
) %>% 
  lapply(htmltools::HTML) 


# map plot of hazard data (grid + census tract level) ----

leaflet(census_tract, height = 800, width = "100%")  %>%
  addTiles() %>%
  addProviderTiles(providers$OpenStreetMap, group = "OSM") %>%
  addProviderTiles(providers$CartoDB.DarkMatter, group = "CartoDB") %>%
  addProviderTiles(providers$Stadia.StamenTonerLite, group = "Toner Lite") %>%
  
  # p_tot ----
addPolygons(data = census_tract,
            group = "Total Population", #change
            fillColor = ~pal_p_tot(p_tot), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_tot, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_tot, #change
            values = census_tract$p_tot, #change
            opacity = 0.9,
            group = "Total Population", #change
            position = "topright",
            title = "Total Population", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # hazard ----
addPolygons(data = census_tract,
            group = "Average Flood Risk Index", #change
            fillColor = ~pal_hazard(Flood_indice_sum_mean), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_hazard, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_hazard, #change
            values = census_tract$Flood_indice_sum_mean, #change
            opacity = 0.9,
            group = "Average Flood Risk Index", #change
            position = "topright",
            title = "Average Flood Risk Index", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_tot_f ----
addPolygons(data = census_tract,
            group = "Female Population", #change
            fillColor = ~pal_p_tot_f(prop1_p_tot_f), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_tot_f, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_tot_f, #change
            values = census_tract$prop1_p_tot_f, #change
            opacity = 0.9,
            group = "Female Population", #change
            position = "topright",
            title = "Share of Female Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_tot_m ----
addPolygons(data = census_tract,
            group = "Male Population", #change
            fillColor = ~pal_p_tot_m(prop1_p_tot_m), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_tot_m, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_tot_m, #change
            values = census_tract$prop1_p_tot_m, #change
            opacity = 0.9,
            group = "Male Population", #change
            position = "topright",
            title = "Share of Male Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_wht ----
addPolygons(data = census_tract,
            group = "White Population", #change
            fillColor = ~pal_p_wht(prop1_p_wht), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_wht, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_wht, #change
            values = census_tract$prop1_p_wht, #change
            opacity = 0.9,
            group = "White Population", #change
            position = "topright",
            title = "Share of White Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_black ----
addPolygons(data = census_tract,
            group = "Black Population", #change
            fillColor = ~pal_p_black(prop1_p_black), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_black, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_black, #change
            values = census_tract$prop1_p_black, #change
            opacity = 0.9,
            group = "Black Population", #change
            position = "topright",
            title = "Share of Black Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_yellow ----
addPolygons(data = census_tract,
            group = "Yellow Population", #change
            fillColor = ~pal_p_yellow(prop1_p_yellow), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_yellow, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_yellow, #change
            values = census_tract$prop1_p_yellow, #change
            opacity = 0.9,
            group = "Yellow Population", #change
            position = "topright",
            title = "Share of Yellow Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_brown ----
addPolygons(data = census_tract,
            group = "Brown Population", #change
            fillColor = ~pal_p_brown(prop1_p_brown), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_brown, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_brown, #change
            values = census_tract$prop1_p_brown, #change
            opacity = 0.9,
            group = "Brown Population", #change
            position = "topright",
            title = "Share of Brown Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_indig ----
addPolygons(data = census_tract,
            group = "Indigenous Population", #change
            fillColor = ~pal_p_indig(prop1_p_indig), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_indig, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_indig, #change
            values = census_tract$prop1_p_indig, #change
            opacity = 0.9,
            group = "Indigenous Population", #change
            position = "topright",
            title = "Indigenous Population in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_0to14yr ----
addPolygons(data = census_tract,
            group = "Population with Age Lesser than 14", #change
            fillColor = ~pal_p_0to14yr(prop1_p_0to14yr), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_0to14yr, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_0to14yr, #change
            values = census_tract$prop1_p_0to14yr, #change
            opacity = 0.9,
            group = "Population with Age Lesser than 14", #change
            position = "topright",
            title = "Share of Population with Age Lesser than 14 in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  
  # p_15to19yr ----
addPolygons(data = census_tract,
            group = "Population with Age Between 15 and 19", #change
            fillColor = ~pal_p_15to19yr(prop1_p_15to19yr), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_15to19yr, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_15to19yr, #change
            values = census_tract$prop1_p_15to19yr, #change
            opacity = 0.9,
            group = "Population with Age Between 15 and 19", #change
            position = "topright",
            title = "Share of Population with Age Between 15 and 19 in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_20to59yr ----
addPolygons(data = census_tract,
            group = "Population with Age Between 20 and 59", #change
            fillColor = ~pal_p_20to59yr(prop1_p_20to59yr), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_20to59yr, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_20to59yr, #change
            values = census_tract$prop1_p_20to59yr, #change
            opacity = 0.9,
            group = "Population with Age Between 20 and 59", #change
            position = "topright",
            title = "Share of Population with Age Between 20 and 59 in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_60+yr ----
addPolygons(data = census_tract,
            group = "Population with Age Above 60", #change
            fillColor = ~pal_p_60.yr(prop1_p_60.yr), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_60.yr, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_60.yr, #change
            values = census_tract$prop1_p_60.yr, #change
            opacity = 0.9,
            group = "Population with Age Above 60", #change
            position = "topright",
            title = "Share of Population with Age Above 60 in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  # p_mean_inc1 ----
addPolygons(data = census_tract,
            group = "Average Income", #change
            fillColor = ~pal_p_mean_inc1(p_mean_inc1), #change
            
            weight = 0.1, opacity = 1, color = "grey", fillOpacity = 0.9,
            
            label = labels_p_mean_inc1, #change
            
            highlightOptions = highlightOptions(color = "black", weight = 2,
                                                bringToFront = FALSE),
            labelOptions = labelOptions(
              style = list("font-weight" = "normal", padding = "3px 6px"), textsize = "15px",direction = "auto")) %>%
  
  # legend 
  addLegend(pal = pal_p_mean_inc1, #change
            values = census_tract$p_mean_inc1, #change
            opacity = 0.9,
            group = "Average Income", #change
            position = "topright",
            title = "Average Income in Tract", #change
            labFormat = labelFormat(suffix = "")) %>%
  
  
  # Layers control ---- 
addLayersControl(
  baseGroups = c("OSM", "CartoDB","Toner Lite"),#,"Toner Lite"
  overlayGroups = c("Total Population", "Average Flood Risk Index", "Female Population", "Male Population",
                    "White Population", "Black Population", "Yellow Population", "Brown Population", "Indigenous Population",
                    "Population with Age Lesser than 14", "Population with Age Between 15 and 19",
                    "Population with Age Between 20 and 59", "Population with Age Above 60",
                    "Average Income"),
  options = layersControlOptions(collapsed = FALSE)) %>%
  hideGroup(c("Average Flood Risk Index", "Female Population", "Male Population",
              "White Population", "Black Population", "Yellow Population", "Brown Population", "Indigenous Population",
              "Population with Age Lesser than 14", "Population with Age Between 15 and 19",
              "Population with Age Between 20 and 59", "Population with Age Above 60",
              "Average Income"))
