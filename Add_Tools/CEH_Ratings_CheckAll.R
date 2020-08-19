#! /usr/bin/Rscript
# .libPaths("C:/Program Files/R/R-3.6.3/library")
# Check that the required packages are installed
# list.of.packages <- c("rnrfa", "tidyverse", "minpack.lm")
# new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
# if(length(new.packages)) install.packages(new.packages)

# -------------------- load the required packages ----------------------
library(rnrfa)
library(tidyverse)
library(minpack.lm)
library(broom)

# -------------------- Functions --------------------------------------

# define function to calcualte Q2 flow exceedance
Q2func <- function(x) {
  tryCatch(expr = {
    df <- tibble(rnrfa::gdf(id = x)) %>%
             rename(flow=1)
    Q.ex <-as.numeric(quantile(df$flow, 0.98))
    return(Q.ex)
  },
  error = function(e){ 
    Q.ex <- as.numeric(NA)
    return(Q.ex)
  })
    
}

# define function to calcualte Q80 flow exceedance
Q80func <- function(x) {
  tryCatch(expr = {
    df <- tibble(rnrfa::gdf(id = x)) %>%
      rename(flow=1)
    Q.ex <-as.numeric(quantile(df$flow, 0.2))
    return(Q.ex)
  },
  error = function(e){ 
    Q.ex <- as.numeric(NA)
    return(Q.ex)
  })
  
}

# function to filter, apply Q exceedance values and rename

add_nrfa_vals <- function(.data, HA_num){
  .data %>%
    filter(`hydrometric-area` %in% HA_num)%>%
    mutate(Q2 = purrr::map_dbl(id, Q2func)) %>%
    mutate(Q80 = purrr::map_dbl(id, Q80func)) %>%
    select(id, `catchment-area`, Q2, Q80, `hydrometric-area`) %>%
    rename(catchmentArea = `catchment-area`, hydroArea = `hydrometric-area`) %>%
    mutate(hydroArea = as_factor(hydroArea)) #%>%
    
}

# function to run power regression returns model obj. and coefs as list
power_reg <- function(.data, colName, s.a, s.b){
  start.L <- list(a=s.a, b=s.b)
  myenc <- enquo(colName)

  m <- .data %>%
    mutate(col_copy = !!myenc) %>%
    nlsLM(col_copy ~ a*catchmentArea^b, data = ., start = start.L)
  tidy_coef <- tidy(coef(m)) %>%
    pull(x)
  
  out_vals <- list(model = m, coefs = tidy_coef)
  
  return (out_vals)
}

# function to generate power equation as string for plotting
power_eqn <- function(.data, mod){
  eq <- substitute(italic(y) == a  ~italic(x)^b,
                   list(a = as.character(format(coef(mod)[1]), digits = 6),
                        b = as.character(format(coef(mod)[2]), digits = 6)))
  
}

# General plotting function for rating curve.
plot_rating <- function(.data, colName, mod.list, Q.level){
  myenc <- enquo(colName)
  df <- .data %>%
    mutate(work_col = !! myenc)
  xl <- max(df$catchmentArea)*0.5
  yl <- max(df$work_col) * 0.5
  
  equation <- power_eqn(., mod.list$model)
  
  df %>%
    ggplot(., aes(x = catchmentArea, y = work_col, label=id)) +
    geom_point(aes(colour=hydroArea)) +
    labs(title = sprintf("Catchment-Area %s Rating: CEH Hydro Area %s", Q.level, req_HA_num),
         x = expression(paste('Contributing Catchment Area ', (km^2))),
         y = expression(paste('Flow ' (m^3/s^-1))),
         colour = 'CEH Hydro Area',
         subtitle = expr(paste(!!equation))) +
    scale_colour_brewer(palette = "Set2") +
    stat_smooth(method = 'nlsLM', formula = 'y~a*x^b', method.args=list(start = c(a = 1, b=1)),se=FALSE) +
    theme_bw()
  
}

# ----------- RUN AND EXPORT ------------

#testing all HA regions:
plot.path <- 'D:/HG_Work/GB_Beaver_Data/Hydro_rating_Checks'

HA.list <- c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
              21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 
             41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 
             61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 
             81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 101, 102, 104, 105)

# Required input is the Hydrometric area number - add from Python script if needed...

# req_HA_num <- as.integer(commandArgs(trailingOnly = TRUE)[1]) # use this when running via python
# req_HA_num = c(101)  # Use this for testing manually

#retrieve summary data for all stations
allStations <- tibble(catalogue())

for (req_HA_num in HA.list) {
  
  # Where There are too few gauges to build a reliable rating - join with neighbours...
  if (req_HA_num %in% c(1, 2, 3, 4, 5, 96, 97)) { # NE Scotland
    hydro_Area_num <- c(1, 2, 3, 4, 5, 96, 97)        
  } else if (req_HA_num %in% c(10, 11)) {  #NE Scotland
    hydro_Area_num <- c(10, 11)
  } else if (req_HA_num %in% c(26, 29, 30)) {  #East England - poor fits combine to improve
    hydro_Area_num <- c(26, 29, 30)
  } else if (req_HA_num %in% c(42, 101)) {  #Join Ilse of White to Hamshire rivers group
    hydro_Area_num <- c(42, 101)
  } else if (req_HA_num %in% c(48, 49)) {  #Cornwall
    hydro_Area_num <- c(48,  49)
  } else if (req_HA_num %in% c(51, 50)) {  #Exemoor - join with Taw and Torridge
    hydro_Area_num <- c(51, 50)
  } else if (req_HA_num %in% c(59, 60)) {  #Loughor Group - join with Towy Group
    hydro_Area_num <- c(59, 60)
  } else if (req_HA_num %in% c(61, 62, 63)) {  #Join West Wales groups
    hydro_Area_num <- c(61, 62, 63)
  } else if (req_HA_num %in% c(64, 65, 66, 102)) {  ## Anglesey and Glasyn Group
    hydro_Area_num <- c(64, 65, 66, 102)  
  } else if (req_HA_num %in% c(69, 70)) {  # Douglas group to Mersey and Irwell
    hydro_Area_num <- c(69, 70)
  } else if (req_HA_num %in% c(73, 74, 75)) {  # Lake District Coastal
    hydro_Area_num <- c(73, 74, 75)
  } else if (req_HA_num %in% c(77, 78)) {  # Annan and Esk
    hydro_Area_num <- c(77, 78)
  } else if (req_HA_num %in% c(80, 81, 82)) {  #Join Doon and Cree groups
    hydro_Area_num <- c(80, 81, 82)
  } else if (req_HA_num %in% c(92, 93, 94, 95, 105)) {  #NW Sotland
    hydro_Area_num <- c(92, 93, 94, 95, 105)
  } else if (req_HA_num %in% c(85, 86,87,88,89, 90, 91, 104)) {  # W Scotland
    hydro_Area_num <- c(85, 86,87,88,89, 90, 91, 104)

  } else 
    hydro_Area_num <- req_HA_num
  

  # Combine station id, Q2 and Q80 values into a dataframe
  
  extr_ceh_tib <- tryCatch(expr = {
    finaltab <- allStations %>%
      add_nrfa_vals(., hydro_Area_num)
  },
  error = function(e){ 
    print(e)
    print(sprintf('NO GAUGES IN HYD. AREA %s', req_HA_num))
    traceback()
    

  })
  
  if(inherits(extr_ceh_tib, "error")) next
  
  if (nrow(finaltab) < 5){
    print(sprintf('< 5 GAUGES IN HYD. AREA %s', req_HA_num))
    next()
  }

  
  Q2.vals <- power_reg(finaltab, colName=Q2, s.a = 500, s.b = 1)  
  Q80.vals <- power_reg(finaltab, colName=Q80, s.a = 500, s.b = 1)
  
  
  # combine coefficients into a list to be returned to python
  Q2_coef_list <- Q2.vals$coefs
  Q80_coef_list <- Q80.vals$coefs
  combClist <- c(Q2_coef_list, Q80_coef_list)
  
  # cat(combClist)
  
  #plotting
  Q2.plt <- plot_rating(finaltab, colName = Q2, mod.list = Q2.vals, Q.level = "Q2")
  q2plt.name <- file.path(plot.path, sprintf('HA_%s_Q2.jpg', req_HA_num))
  ggsave(q2plt.name, plot=Q2.plt)
  
  Q80.plt <- plot_rating(finaltab, colName = Q80, mod.list = Q80.vals, Q.level = "Q80")
  q80plt.name <- file.path(plot.path, sprintf('HA_%s_Q80.jpg', req_HA_num))
  ggsave(q80plt.name, plot = Q80.plt)
}
