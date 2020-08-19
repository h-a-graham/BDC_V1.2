#! /usr/bin/Rscript
.libPaths("C:/Program Files/R/R-3.6.3/library")
# Check that the required packages are installed
# list.of.packages <- c("rnrfa", "tidyverse", "minpack.lm")
# new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
# if(length(new.packages)) install.packages(new.packages)

# load the required packages
library(rnrfa)
library(tidyverse)
library(minpack.lm)

# Required input is the Hydrometric area number - add from Python script if needed...

hydro_Area_num <- as.integer(commandArgs(trailingOnly = TRUE)[1]) # use this when running via python
hydro_Area_num = c(21)  # Use this for testing manually

if (hydro_Area_num == 102) {  # This if statement serves to correct regions contained within Hydrological areas that contain too few gauging stations
  hydro_Area_num <- c(102, 65)        # This is corrected by selecting an appropriate alternative catchment with comparable hydrology.
}                             # Currently this applies to HA 102 (Anglesey)
  


if (hydro_Area_num %in% c(1, 2, 3, 95, 96, 97)) {  # Very few gauges in far North of Scotland... combine region #need to rethink this?
  hydro_Area_num <- c(1, 2, 3, 95, 96, 97)
}


if (hydro_Area_num %in% c(86,87,88,89,104)) {  # combine some western scotland regions.
  hydro_Area_num <- c(86,87,88,89,104)
}

#retrieve summary data for all stations
allStations <- catalogue()

#subset all stations within hydrometric area
hyd_Area <- allStations[allStations$`hydrometric-area` %in% hydro_Area_num,]

#convert to list of station numbers
hyd_list <- as.list(hyd_Area$id)
# print(hyd_list)

# Create initial list:
myList <- list()
#Loop over list and retrieve all daily mean flow data for each station
for (i in hyd_list){
  tryCatch({
  # print(i)

  df <- data.frame(rnrfa::gdf(id = i))
  colnames(df) <- i

  myList[[length(myList)+1]] <- df}, error=function(e){})

}

# define function to calcualte Q2 flow exceedance
Q2func <- function(x, i) {
  quantile(x[,i],0.98)
}
# define function to calcualte Q80 flow exceedance
Q80func <- function(x, i) {
  quantile(x[,i],0.2)
}
# define function to calcualte gauge id
getnames <- function(x) {
  colnames(x)
}

# Combine station id, Q2 and Q80 values into a dataframe
catch_names <- data.frame(do.call(rbind,lapply(myList, getnames)))
names(catch_names) <- "id"
catch_names <- (merge(catch_names, allStations, by = 'id'))
# catch_names <- data.frame(catch_names$id, catch_names$`catchment-area`)
catch_names$`catchment-area` <- as.numeric(as.character(catch_names$`catchment-area`))
Q2 <- data.frame(do.call(rbind,lapply(myList, Q2func)))
Q80<- data.frame(do.call(rbind,lapply(myList, Q80func)))
# catch_Area <- allStations$catchmentArea
finaltab <- data.frame(cbind(catch_names$id, catch_names$`catchment-area`, Q2$X98., Q80$X20., catch_names$`hydrometric-area`))
colnames(finaltab) <- c("id","catchmentArea", "Q2", "Q80", "hydroArea")
# finaltab$catchmentArea<- as.numeric(finaltab$`catchment-area`)
# finaltab$Q2 <- as.numeric(finaltab$Q2)
# finaltab$Q80 <- as.numeric(finaltab$Q80)
finaltab$hydroArea <- as.factor(as.numeric(finaltab$hydroArea))

# zero.tab <- data.frame(0,0,0,0,0)
# colnames(zero.tab) <- c("id","catchmentArea", "Q2", "Q80", "hydroArea")
# zero.tab$hydroArea <- as.factor(as.numeric(zero.tab$hydroArea))
# 
# zero.tab <-zero.tab %>% slice(rep(row_number(), 100))
# 
# finaltab <- rbind(finaltab,zero.tab)

# calculating Power equation or really a non-linear least squares fit. for Q2~catchmentArea and Q80~catchmentArea
start.L = list(a =500,b=1)
m = nlsLM(Q2 ~ a*catchmentArea^b, data = finaltab, start = start.L)
c1 <- as.numeric(as.character(format(coef(m)[1], digits = 2)))
c2 <- as.numeric(as.character(format(coef(m)[2], digits = 2)))

m = nlsLM(Q80 ~ a*catchmentArea^b, data = finaltab, start = start.L)
c3 <- as.numeric(as.character(format(coef(m)[1], digits = 2)))
c4 <- as.numeric(as.character(format(coef(m)[2], digits = 2)))

# combine coefficients into a list to be returned to python
Q2_coef_list <- c(c1, c2)
Q80_coef_list <- c(c3, c4)
combClist <- c(c1, c2, c3, c4)

cat(combClist)

# # ------------------ Section for plotting --------------------------
power_eqnQ2 = function(df, start = list(a =500,b=1)){
  m = nlsLM(Q2 ~ a*catchmentArea^b, start = start, data = df);
  eq <- substitute(italic(y) == a  ~italic(x)^b,
                   list(a = format(coef(m)[1], digits = 2),
                        b = format(coef(m)[2], digits = 2)))
  format(coef(m)[1])
  as.character(as.expression(eq));

}
power_eqnQ80 = function(df, start = list(a =500,b=1)){
  m = nlsLM(Q80 ~ a*catchmentArea^b, start = start, data = df);
  eq <- substitute(italic(y) == a  ~italic(x)^b,
                   list(a = format(coef(m)[1], digits = 2),
                        b = format(coef(m)[2], digits = 2)))
  format(coef(m)[1])
  as.character(as.expression(eq));

}

xlabQ2 <- max(finaltab$catchmentArea)*0.5
ylabQ2 <- max(finaltab$Q2)*0.9

plot_Q2 <- ggplot(finaltab, aes(x = catchmentArea, y = Q2, label=id)) +
  geom_point(aes(colour=hydroArea)) +
  scale_colour_brewer(palette = "Set1") +
  # geom_text(aes(label=id),hjust=0, vjust=0) +
  # stat_smooth(method = 'lm', aes(colour = 'linear'),se=FALSE) +
  # stat_smooth(method="lm", se=FALSE,
  #             formula=y ~ poly(x, 3, raw=TRUE)-1) +
  stat_smooth(method = 'nlsLM', formula = 'y~a*x^b', method.args=list(start = c(a = 1, b=1)),se=FALSE) +
  geom_text(x = xlabQ2, y = ylabQ2, label = power_eqnQ2(finaltab), parse = TRUE)
plot_Q2

xlabQ80 <- max(finaltab$catchmentArea)*0.5
ylabQ80 <- max(finaltab$Q80)*0.9

plot_Q80 <- ggplot(finaltab, aes(x = catchmentArea, y = Q80, label=id), colour=) +
  geom_point(aes(colour=hydroArea)) +
  scale_colour_brewer(palette = "Set1") +
  # geom_text(aes(label=id),hjust=0, vjust=0) +
  # stat_smooth(method = 'lm', aes(colour = 'linear'),se=FALSE) +
  # stat_smooth(method="lm", se=FALSE,
  #             formula=y ~ poly(x, 2, raw=TRUE),aes(colour = 'poly 2')) +
  stat_smooth(method = 'nlsLM', formula = 'y~a*x^b', method.args=list(start = c(a = 1, b=1)),se=FALSE) +
  geom_text(x = xlabQ80, y = ylabQ80, label = power_eqnQ80(finaltab), parse = TRUE)
plot_Q80

#
#
