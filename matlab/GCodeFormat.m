function core = GCodeFormat(layer, prtOpt)
%% Create gcode 
% parse layer structure to create gcode and calculate extrusion values

%2 steps: first create raw gcode file, then merge it into another with all
%the necessary parameters for the gcode 

fid = fopen(prtOpt.gcode_fname, 'w');

nLayer = size(layer,2);


tot_filament_needed = 0;
tot_time_spent = 0;


if (nLayer == 1)&&(prtOpt.nLayers>1) %replicate a single layer if needed 
    for i = 2:prtOpt.nLayers
        layer(i) = layer(1); 
    end
end
nLayer = size(layer,2);

for part_num = 1:(prtOpt.nRepeats)

    fprintf(fid, '\n;NEW PART'); 
    if part_num>1  %we assume that first print has already been positioned in the right location 
        	layer = movePrint(layer,[((maxx-minx) + 2) 0],0);
    end
    curr_x = layer(1).Course(1).POINT(1,1);
    curr_y = layer(1).Course(1).POINT(1,2);
    curr_z = layer(1).Course(1).POINT(1,3);
    
    
    minx = curr_x; maxx = curr_x; 
    miny = curr_y; maxy = curr_y; 
    
    for layer_num = 1:nLayer

        ncourses = size(layer(layer_num).Course,2);
        fprintf(fid, '\n;LAYER %d', layer_num);
        
        for course_num = 1:ncourses
            fprintf(fid, '\n;COURSE %d', course_num);
    
            npoints = size(layer(layer_num).Course(course_num).POINT,1);
            start_x = layer(layer_num).Course(course_num).POINT(1,1);
            start_y = layer(layer_num).Course(course_num).POINT(1,2);
            start_z = prtOpt.layer_height*layer_num;
    
            %last curr_xyz values are still the previous course
                dist = pdist2([start_x, start_y, start_z], [curr_x, curr_y, curr_z], 'euclidean');
                if dist > prtOpt.thresh_traveldist
    
                    %fprintf(fid,'\nG10');
                    fprintf(fid,'\nG1 E-0.8 F2100');
                    fprintf(fid, '\nG1 Z%4.4f', start_z + 1);
                    fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f', start_x, start_y, start_z + 1);
                    %fprintf(fid,'\nG11');
                    fprintf(fid,'\nG1 E0.8 F1500');

    %                 [layer_num course_num] ;
%                 else
%                     fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f', start_x, start_y, start_z);
                end
    
            fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f', start_x, start_y, start_z);
            
            for point_num = 2:npoints
                
                curr_x = layer(layer_num).Course(course_num).POINT(point_num,1);
                curr_y = layer(layer_num).Course(course_num).POINT(point_num,2);
                curr_z = prtOpt.layer_height*layer_num;
                
                width = layer(layer_num).Course(course_num).POINT(point_num,4);
                height = prtOpt.layer_height; %layer(layer_num).Course(course_num).POINT(point_num,5);
                
                dist = pdist2([start_x, start_y, start_z], [curr_x, curr_y, curr_z], 'euclidean');
                extrusion = 4*(dist*height*width)/(pi*prtOpt.fil_dia^2);
    
                fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f E%4.4f F%d', curr_x, curr_y, curr_z, extrusion, prtOpt.print_speed);
                tot_filament_needed = tot_filament_needed + extrusion; 
                tot_time_spent = tot_time_spent + dist/prtOpt.print_speed;
                
                start_x = curr_x;
                start_y = curr_y;
                start_z = curr_z;
    
                if minx>curr_x
                    minx = curr_x; 
                end
                if miny>curr_y
                    miny = curr_y; 
                end
                if maxx<curr_x
                    maxx = curr_x; 
                end
                if maxy<curr_y
                    maxy = curr_y; 
                end
    
             end
        end
        
    end

    %END FOR EACH PART 
    if strcmp(prtOpt.ironingFrame,'yes') %%yes if extra toolpaths should be added to smear the long edges
        fprintf(fid, '\nG1 Z%4.4f', (curr_z + 1)); 
        fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f F%d', minx, miny, curr_z, prtOpt.print_speed);
        fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f F%d', maxx, miny, curr_z, prtOpt.print_speed);
        fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f F%d', maxx, maxy, curr_z, prtOpt.print_speed);
        fprintf(fid, '\nG1 X%4.4f Y%4.4f Z%4.4f F%d', minx, maxy, curr_z, prtOpt.print_speed);
    end
    
    if strcmp(prtOpt.ControlSeedPoint,'yes') %SENT 
        fprintf(fid, '\n;MARK NOTCH AT MIDDLE'); 
        fprintf(fid, '\nG10'); 
        fprintf(fid, '\nG1 Z%4.4f', (curr_z + 1)); 
        fprintf(fid, '\nG1 X%4.4f Y%4.4f', (minx+maxx)/2,(miny+maxy)/2);
        fprintf(fid, '\nG1 Z%4.4f', curr_z); %mark the sample
        fprintf(fid, '\nG1 Z%4.4f', curr_z + 10);%mlift nozzle for next print if exists
        fprintf(fid, '\n;END'); 
        fprintf(fid, '\nG11'); 
        
    end

end


fclose(fid);

%calculate useful stats 
flav = ';FLAVOR: MARLIN\n';
gen = char("\n;Generated with Slith3r (Shaping Matter Lab) on " + string(datetime('today'))); 
nozdiam = sprintf('\n;Nozzle diameyer: %4.2f',prtOpt.fil_dia);
fil = sprintf('\n;Total length of filament needed (m): %f',tot_filament_needed/1000);
estTime = sprintf('\n;Estimated Time (min): %f',tot_time_spent);
numLay = sprintf('\n;Number of Layers: %d',nLayer);



%second step: concatenate all chuncks 
begin_str = [flav gen nozdiam fil estTime numLay];
begin_str2 = fileread(strcat(prtOpt.gcodeExtremes_foldername, 'begin_text.gcode'));
core = fileread(prtOpt.gcode_fname); 
end_str = fileread(strcat(prtOpt.gcodeExtremes_foldername, 'end_text.gcode'));

merge = [begin_str, char(10), begin_str2, char(10), core, char(10), end_str]; 
    
fid = fopen(prtOpt.gcode_fname, 'w'); 
if fid == -1, error('Cannot open file %s', prtOpt.gcode_fname); 
end
fwrite(fid, merge, 'char');
fclose(fid);




end