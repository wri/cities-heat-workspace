library(lidR)
library(terra)
library(tidyterra)
library(sf)
library(tidyverse)
library(here)



# LULC --------------------------------------------------------------------


lulc_solweig_raster <- rast(here("data", "ZAF-Cape_town", "processed", 
                                 "landcover_nozero.tif"))

# Streets
streets <- rast(here("data", "ZAF-Cape_town", "processed", 
                     "ZAF-Cape_town-LULCv2.tif")) == 30 
streets <- streets %>% 
  resample(lulc_solweig_raster, method = "max") 


# LULC
lulc_raster <- rast(here("data", "ZAF-Cape_town", "processed", 
                         "ZAF-Cape_town-LULCv2.tif")) %>% 
  as.factor() %>% 
  resample(lulc_solweig_raster, method = "near")

lulc_resample <- max(lulc_raster, (streets * 30)) %>% 
  as.factor()

# Pixels adjacent to streets
# set 0's to NA to create a buffer of only roads
streets_NA <- subst(streets, 0, NA)

# 6-meter buffer (2 pixels)
streets_buff <- streets_NA %>% 
  buffer(6) %>% 
  as.numeric()

streets_buff <- streets_buff - streets

# Buildings
# buildings buffer (1 pixel)
builds <- lulc_resample == 40
builds_NA <- subst(builds, 0, NA)

builds_buff <- builds_NA %>% 
  buffer(3)

builds_buff <- abs(builds_buff - builds - 1)

# Plantable area
# green space, built up other, barren, open space, parking can be planted
# water, roads, building,  cannot
reclass <- matrix(c(1, 1,
                    2, 1, 
                    3, 1,
                    10, 1,
                    20, 0, 
                    30, 0,
                    40, 0,
                    50, 0), 
                  ncol = 2, byrow = TRUE)

plantable_lulc <- lulc_resample %>% 
  classify(reclass) 

# All plantable area
# subtract building buffer
plantable_lulc <- plantable_lulc * builds_buff

# Street plantable area
plantable_street <- plantable_lulc * streets_buff

# Trees -------------------------------------------------------------------
# tree_cover_lidar <- rast(here("data", "ZAF-Cape_town", "processed", 
#                         "canopyheight_lidar.tif")) 

# tree cover from Cape Town lidar, height greater than or equal to 1 meter
tree_cover <- rast(here("data", "ZAF-Cape_town", "processed", 
                        "ZAF-Cape_Town-citycentre_roi-tree_canopy_height.tif")) %>% 
  resample(lulc_solweig_raster, method = "bilinear")

names(tree_cover) <- "height"

ggplot() + 
  geom_spatraster(data = tree_cover)

# binary tree cover
no_trees <- tree_cover < 1


# Street plantable area without tree cover
plantable_street <- plantable_street * no_trees

tree_cover <- tree_cover %>% 
  subst(0, NA)

# Tree planting scenario --------------------------------------------------

sample_points_min_distance <- function(plantable_points, n_points, min_distance) {

  # Initialize an empty list to store valid points
  valid_points <- list()
  
  # Convert sf object to matrix of coordinates for easier handling
  coords <- sfheaders::sf_to_df(plantable_points)
  
  # Randomly shuffle the coordinates
  # set.seed(5511)  # Set seed for reproducibility
  shuffled_coords <- coords[sample(nrow(coords)), ]
  
  # Add the first point to the valid points list
  valid_points[[1]] <- shuffled_coords[1, ]
  
  # Iterate through the shuffled coordinates and add points if they meet the distance criterion
  for (i in 2:nrow(shuffled_coords)) {
    dist_to_valid_points <- sapply(valid_points, function(pt) {
      st_distance(st_point(c(pt$x, pt$y)), st_point(c(shuffled_coords[i, ]$x, shuffled_coords[i, ]$y)))
    })
    
    if (all(dist_to_valid_points >= min_distance)) {
      valid_points[[length(valid_points) + 1]] <- shuffled_coords[i, ]
      if (length(valid_points) == n_points) break
    }
  }
  
  # Combine the valid points into an sf object
  valid_points_df <- do.call(rbind, valid_points)
  valid_points_sf <- st_as_sf(valid_points_df, coords = c("x", "y"), crs = st_crs(plantable_points))
  
  return(valid_points_sf)
}

# Get tree height and area for local maxima
# locate trees
ttops <- lidR::locate_trees(tree_cover, lmf(9))

# segment crowns
crowns <- lidR::dalponte2016(tree_cover, ttops)()

# Plot individual trees
ggplot() +
  geom_spatraster(data = as.factor(crowns)) + 
  scale_fill_manual(values = pastel.colors(5638), guide="none") +
  theme(legend.position="none")

tree_pixels <- as.data.frame(crowns) %>% 
  rename(treeID = height) %>% 
  group_by(treeID) %>% 
  summarize(count = n()) %>% 
  left_join(st_drop_geometry(ttops), by = "treeID") %>% 
  rename(height = Z)

ggplot(tree_pixels) +
  geom_density(aes(x = height))

ggplot(tree_pixels) +
  geom_density(aes(x = count))

ggplot(tree_pixels) +
  geom_hex(aes(x = height, y = count))

# Tree heights
q1 <- ceiling(quantile(tree_pixels$height, 0.25))
q2 <- ceiling(quantile(tree_pixels$height, 0.50))
q3 <- ceiling(quantile(tree_pixels$height, 0.75))

# Assign heights and area in pixels (1 x 1, 3 x 3, 5 x 5)
tree_sizes <- tribble(
  ~ height, ~ area, ~weight,
  q1, 1, 0.1,
  q2, 3, 0.8, 
  q3, 5, 0.1,
)

# Age existing trees
# Add q1 value to trees in q1, q2 to q2, q3 to q3
tree_cover_aged <- tree_cover %>% 
  mutate(aged_height = case_when(height < q1 ~ height + q1,
                                 height >= q1 & height < q2 ~ height + q2 - q1,
                                 height >= q2 & height < q3 ~ height + q3 - q2,
                                 height >= q3 ~ height))

ggplot() +
  geom_spatraster(data = tree_cover_aged$aged_height)


# Define function to expand points to specified number of cells
generate_trees <- function(numTrees, minDist, plantable) {
  # Convert plantable area to points
  plantable_points <- plantable %>% 
    subst(0, NA) %>% 
    as.points() %>% 
    st_as_sf() 
  
  # Create an empty raster with the same resolution and extent as raster1
  template_raster <- subst(tree_cover * 0, 0, NA) 
  
  # Sample tree sizes
  sampled_points <- sample_points_min_distance(plantable_points, numTrees, minDist)
  
  tree_points <- tree_sizes %>% 
    sample_n(numTrees, replace = TRUE, weights = weight) %>% 
    bind_cols(sampled_points) %>% 
    st_as_sf()
  
  for (i in seq_len(nrow(tree_points))) {
    point <- st_as_sf(tree_points[i, ])
    size <- point$area
    x <- st_coordinates(point)[1]
    y <- st_coordinates(point)[2]
    
    # Calculate the number of cells to cover in each direction
    cell_res <- res(template_raster)
    
    # Define the extent to cover
    xmin <- x - size * cell_res[1]
    xmax <- x + size * cell_res[1]
    ymin <- y - size * cell_res[2]
    ymax <- y + size * cell_res[2]
    
    # Create a smaller raster to represent the expanded point
    point_raster <- crop(template_raster, ext(xmin, xmax, ymin, ymax))
    values(point_raster) <- point$height
    
    # Update the main raster
    template_raster <- mosaic(template_raster, point_raster, fun = "max")
    
  }
  
  # return(template_raster)
  output <- list(template_raster, tree_points)
  return(output)
}

# Use the function to convert tree_points to raster
sc_50r_streetTrees <- generate_trees(numTrees = 50, minDist = 10, plantable = plantable_street)
sc_50r_streetTrees_rast <- max(subst(sc_50r_streetTrees[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_50r_streetTrees_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_50r_streetTrees_rast.tif"))
sc_50r_streetTrees_pts <- sc_50r_streetTrees[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_50r_streetTrees_rast, 0, NA)) +
  geom_sf(data = sc_50r_streetTrees_pts, color = "red", fill = NA, size = 2) #, pch = 21)

sc_100r_streetTrees <- generate_trees(numTrees = 100, minDist = 10, plantable_street) 
sc_100r_streetTrees_rast <- max(subst(sc_100r_streetTrees[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_100r_streetTrees_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_100r_streetTrees_rast.tif"))
sc_100r_streetTrees_pts <- sc_100r_streetTrees[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_100r_streetTrees_rast, 0, NA)) +
  geom_sf(data = sc_100r_streetTrees_pts, color = "red", fill = NA, size = 2) #, pch = 21)


# plantable area within parks
parks <- lulc_resample %in% c(1, 10)
plantable_parks <- parks * plantable_lulc

sc_50r_parkTrees <- generate_trees(numTrees = 50, minDist = 10, plantable = plantable_parks)  
sc_50r_parkTrees_rast <- max(subst(sc_50r_parkTrees[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_50r_parkTrees_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_50r_parkTrees_rast.tif"))
sc_50r_parkTrees_pts <- sc_50r_parkTrees[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_50r_parkTrees_rast, 0, NA)) +
  geom_sf(data = sc_50r_parkTrees_pts, color = "red", fill = NA, size = 2, pch = 21)

sc_100r_parkTrees <- generate_trees(numTrees = 100, minDist = 10, plantable = plantable_parks)  
sc_100r_parkTrees_rast <- max(subst(sc_100r_parkTrees[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_100r_parkTrees_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_100r_parkTrees_rast.tif"))
sc_100r_parkTrees_pts <- sc_100r_parkTrees[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_100r_parkTrees_rast, 0, NA)) +
  geom_sf(data = sc_100r_parkTrees_pts, color = "red", fill = NA, size = 2, pch = 21)

# plantable area along street of interest
street_aoi <- st_read(here("data", "ZAF-Cape_town", "street-aoi-poly.shp")) %>% 
  rasterize(subst(tree_cover * 0, 0, NA), value = 1) %>% 
  subst(NA, 0)

street_aoi_plantable <- street_aoi * plantable_street

ggplot() +
  geom_spatraster(data = street_aoi_plantable) 

sc_50r_streetTrees_aoi <- generate_trees(numTrees = 50, minDist = 10, plantable = street_aoi_plantable)
sc_50r_streetTrees_aoi_rast <- max(subst(sc_50r_streetTrees_aoi[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_50r_streetTrees_aoi_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_50r_streetTrees_aoi_rast.tif"))
sc_50r_streetTrees_aoi_pts <- sc_50r_streetTrees_aoi[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_50r_streetTrees_aoi_rast, 0, NA)) +
  geom_sf(data = sc_50r_streetTrees_aoi_pts, color = "red", fill = NA, size = 2, pch = 21)

sc_100r_streetTrees_aoi <- generate_trees(numTrees = 100, minDist = 10, plantable = street_aoi_plantable)
sc_100r_streetTrees_aoi_rast <- max(subst(sc_100r_streetTrees_aoi[[1]], NA, 0), tree_cover_aged$aged_height, na.rm = TRUE)
writeRaster(sc_100r_streetTrees_aoi_rast, here("data", "ZAF-Cape_Town", "scenarios", "sc_100r_streetTrees_aoi_rast.tif"))
sc_100r_streetTrees_aoi_pts <- sc_100r_streetTrees_aoi[[2]]

ggplot() +
  geom_spatraster(data = subst(sc_100r_streetTrees_aoi_rast, 0, NA)) +
  geom_sf(data = sc_100r_streetTrees_aoi_pts, color = "red", fill = NA, size = 2, pch = 21)


# # Modeling joint distribution of tree height and area ---------------------
# 
# 
# # Estimating exponential rates 
# # (https://stats.stackexchange.com/questions/76994/how-do-i-check-if-my-data-fits-an-exponential-distribution)
# tree_dat <- data.frame(height = tree_pixels$height,
#                        area = as.numeric(tree_pixels$count))
# 
# fit1 <- MASS::fitdistr(tree_dat$height, "exponential")
# ks.test(tree_dat$height, "pexp", fit1$estimate)
# plot(density(rexp(40, rate = fit1$estimate)))
# lines(density(tree_dat$height))
# 
# fit2 <- MASS::fitdistr(tree_dat$area, "exponential")
# ks.test(tree_dat$area, "pexp", fit1$estimate)
# plot(density(rexp(40, rate = fit2$estimate)))
# lines(density(tree_dat$area))
# 
# # draw from multivariate exponential
# # https://rdrr.io/rforge/lcmix/man/mvexp.html
# set.seed(5511)
# tree_distr <- lcmix::rmvexp(10000, rate = c(fit1$estimate, fit2$estimate), corr = cor(tree_dat)) %>% 
#   as.data.frame() 
# colnames(tree_distr) <-  c("height", "area")
# 
# 
# ggplot() +
#   geom_density(data = tree_dat, aes(x = height), color = "blue") +
#   geom_density(data = tree_distr, aes(x = height), color = "red") 
# 
# ggplot() +
#   geom_density(data = tree_dat, aes(x = area), color = "blue") +
#   geom_density(data = tree_distr, aes(x = area), color = "red") 
# 
# model_distr <- tree_distr %>% 
#   mutate(height2 = ceiling(height),
#          area2 = )
# 
# ggplot() +
#   geom_point(data = tree_dat, aes(x = height, y = area), color = "blue", alpha = 0.2) +
#   geom_point(data = tree_distr, aes(x = height, y = area), color = "red", alpha = 0.2) 
# 
# # Conditional sampling from the theoretical distribution
# # identify the 50th and 75th percentiles
# percentiles_25 <- apply(tree_distr, 2, function(x) quantile(x, 0.25))
# percentiles_50 <- apply(tree_distr, 2, function(x) quantile(x, 0.5))
# percentiles_75 <- apply(tree_distr, 2, function(x) quantile(x, 0.75))
# 
# # Filter samples to retain those between the 50th and 75th percentiles
# filtered_samples <- tree_distr
# for (i in 1:2) {
#   filtered_samples <- filtered_samples[filtered_samples[,i] >= percentiles_25[i] & 
#                                          filtered_samples[,i] <= percentiles_75[i], ]
# }
# 
# 
# # intersect trees with streets buffer to get street trees
# street_trees <- trees %>% 
#   filter(lengths(st_intersects(., streets_buff)) > 0)
# 
# # get pixel values for street trees
# street_tree_heights <- tree_cover %>% 
#   terra::extract(street_trees)
# 
# ggplot(street_tree_heights) +
#   geom_boxplot(aes(x = canopyheight_lidar))
# 
# # get 25th, 50th, and 75th percentile height values
# small_tree <- quantile(street_tree_heights$canopyheight_lidar, probs = 0.25, names = FALSE)
# med_tree <- quantile(street_tree_heights$canopyheight_lidar, probs = 0.50, names = FALSE)
# large_tree <- quantile(street_tree_heights$canopyheight_lidar, probs = 0.75, names = FALSE)
#   
# # ggplot(tree_height) +
# #   geom_boxplot(aes(x = height))
# # st_write(trees, here("data", "ZAF-Cape_town", "processed", "trees.shp"))
# 
# 
# 
# tree_height <- data.frame(tree_cover) %>% 
#   rename(height = canopyheight_lidar) %>% 
#   filter(height >= 1)
