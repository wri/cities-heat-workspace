library(terra)
library(tidyterra)
library(sf)
library(tidyverse)
library(ggnewscale)
library(here)

# All trees and roads
streets <- rast(here("data", "ZAF-Cape_town", "processed", 
                     "ZAF-Cape_town-LULCv2.tif")) == 30 

tree_cover <- rast(here("data", "ZAF-Cape_town", "processed", "ZAF-Cape_Town-submeterTree.tif"))  
tree_cover <- tree_cover %>% 
  project(streets) >= 1

streets_trees <- max(tree_cover * 2, streets)
streets_trees <- subst(streets_trees, 0, NA)
writeRaster(streets_trees, here("Maps", "ZAF-Cape_Town", "streets_trees.tif"), overwrite = TRUE)

ggplot() +
  geom_spatraster(data = as.factor(streets_trees), na.rm = TRUE) +
  scale_fill_manual(values = c("darkgrey", "darkgreen"), 
                    labels = c("Road", "Trees"),
                    name = "",
                    na.translate = F) +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank())

ggsave(here("Maps", "ZAF-Cape_Town", "streets_trees.png"))

# Trees, street trees, and roads
streets_buff <- streets %>% 
  subst(0, NA) %>% 
  buffer(6) 

street_trees <- tree_cover * streets_buff

streets_trees_types <- max(street_trees * 3, streets_trees)
writeRaster(streets_trees_types, here("Maps", "ZAF-Cape_Town", "streets_trees_types.tif"), overwrite = TRUE)

ggplot() +
  geom_spatraster(data = as.factor(streets_trees_types), na.rm = TRUE) +
  scale_fill_manual(values = c("darkgrey", "darkgreen", "palegreen3"), 
                    labels = c("Road", "Trees", "Street Trees"),
                    name = "",
                    na.translate = F) +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank())

ggsave(here("Maps", "ZAF-Cape_Town", "streets_trees_types.png"))

# Plantable area
reclass <- matrix(c(1, 1,
                    2, 1, 
                    3, 1,
                    10, 1,
                    20, 0, 
                    30, 0,
                    40, 0,
                    50, 0), 
                  ncol = 2, byrow = TRUE)

plantable <- rast(here("data", "ZAF-Cape_town", "processed", 
                            "ZAF-Cape_town-LULCv2.tif")) %>% 
  classify(reclass) %>% 
  subst(0, NA)

plantable <- plantable - tree_cover

plantable_streets_trees <- max(streets_trees, plantable + 2, na.rm = TRUE) 
writeRaster(plantable_streets_trees, here("Maps", "ZAF-Cape_Town", "plantableArea_streets_trees.tif"), overwrite = TRUE)

ggplot() +
  geom_spatraster(data = as.factor(plantable_streets_trees), na.rm = TRUE) +
  scale_fill_manual(values = c("darkgrey", "darkgreen", "yellow"), 
                    labels = c("Road", "Trees", "Plantable area"),
                    name = "",
                    na.translate = F) +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank())

ggsave(here("Maps", "ZAF-Cape_Town", "plantableArea_streets_trees.png"))

# street tree potential
street_tree_potential <- plantable * streets_buff
street_tree_potential <- subst(street_tree_potential, 0, NA)

street_tree_potential2 <- max(street_tree_potential + 2, streets_trees, na.rm = TRUE)
writeRaster(street_tree_potential2, here("Maps", "ZAF-Cape_Town", "street_tree_potential.tif"), overwrite = TRUE)
street_tree_potential2 <- rast(here("Maps", "ZAF-Cape_Town", "street_tree_potential.tif"))

ggplot() +
  geom_spatraster(data = as.factor(street_tree_potential2), na.rm = TRUE) +
  scale_fill_manual(values = c("darkgrey", "darkgreen", "yellow"), 
                    labels = c("Road", "Existing trees", "Street tree potential"),
                    name = "",
                    na.translate = F) +
  theme(axis.title.x=element_blank(),
        axis.text.x=element_blank(),
        axis.ticks.x=element_blank(),
        axis.title.y=element_blank(),
        axis.text.y=element_blank(),
        axis.ticks.y=element_blank())

ggsave(here("Maps", "ZAF-Cape_Town", "street_tree_potential.png"))

# open space potential