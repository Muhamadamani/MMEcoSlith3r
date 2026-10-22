function layerReorder = ReorderPaths(LAYER,prtOpt)
    nLayer = size(LAYER, 2);

    % if a frame is made, boundary layer should be last thus excluded from
    % the reordering of paths 
    if prtOpt.frameBool == 1 
        layer_woBoundary = LAYER; 
        clear LAYER
        for lnum = 1:nLayer
            ncourses = size(layer_woBoundary(lnum).Course,2);
            LAYER(lnum).Course = layer_woBoundary(lnum).Course(1:end-1);
        end
    end

    % get start & end points of each course 
    for lnum = 1:nLayer
        ncourses = size(LAYER(lnum).Course,2);
        
        for cnum = 1:ncourses
            LAYER(lnum).start_pts(cnum,:) = LAYER(lnum).Course(cnum).POINT(1,1:2);
            LAYER(lnum).end_pts(cnum,:) = LAYER(lnum).Course(cnum).POINT(end,1:2);
        end    

        if strcmp(prtOpt.ControlSeedPoint,'yes')
              %FUTURE: sort the lines according to the edge, since they are likely to be
              %mostly all parallel. This avoids the first line to be in the middle of
              %the print 
              %for now: only sort starting points according to X direction 
%              xmin = min(prtOpt.Edge(:,1)); ymin = min(prtOpt.Edge(:,2)); 
             temp = LAYER(lnum).start_pts;  
             [~,index] = sort([temp]);
             temp2 = [struct2cell(LAYER(lnum).Course)];  temp2 = squeeze(temp2); 
             temp2 = temp2(index(:,1)); 
            for i = 1:length(temp2)
                LAYER(lnum).Course(i) = struct('POINT',temp2{i}); 
            end
             b = LAYER(lnum).start_pts(index(:,1),:);
             c = LAYER(lnum).end_pts(index(:,1),:);
             LAYER(lnum).start_pts =  b;
             LAYER(lnum).end_pts = c; 
        end
    end


    % find 
    for lnum = 1:nLayer
        ncourses = size(LAYER(lnum).Course,2);
        
        for cnum = 1:ncourses-1


                current_pt_start_end = LAYER(lnum).end_pts(cnum,:)         ;  
                following_start_end = vertcat(LAYER(lnum).start_pts(cnum+1:end,:),...
                                              LAYER(lnum).end_pts(cnum+1:end,:)); %first half is made of starts, second is made of ends 
                
                dists = pdist2(following_start_end, current_pt_start_end, 'euclidean'); %find among all extremities that haven't been printed, which is the closest 
                
                idx = find(dists == min(dists),1);
%                 if size(LAYER(lnum).Course(cnum).POINT,1) == 2
%                     
%                 else
                
                % swap location of next course with the one with the closest point
                
                if idx > size(following_start_end,1)/2  % idx is in the second half of the list so the end point of a course was closest
                    course_num_to_swap = cnum + idx - size(following_start_end,1)/2;
                    
                    %swap the closest course with next one in line, and
                    %flip it 
                    if (cnum+1) == course_num_to_swap %next one is also the closest one!
                        temp = LAYER(lnum).Course(cnum+1).POINT; 
                        LAYER(lnum).Course(course_num_to_swap).POINT = flipud(temp); 
                        LAYER(lnum).start_pts(cnum+1,:) = LAYER(lnum).Course(cnum+1).POINT(1,1:2);
                        LAYER(lnum).end_pts(cnum+1,:) = LAYER(lnum).Course(cnum+1).POINT(end,1:2);
                    else
                        temp = LAYER(lnum).Course(cnum+1);
                        LAYER(lnum).Course(cnum+1).POINT = flipud(LAYER(lnum).Course(course_num_to_swap).POINT);
                        LAYER(lnum).Course(course_num_to_swap) = temp;
                    
                        % update start and end points vector
                        LAYER(lnum).start_pts(cnum+1,:) = LAYER(lnum).Course(cnum+1).POINT(1,1:2);
                        LAYER(lnum).end_pts(cnum+1,:) = LAYER(lnum).Course(cnum+1).POINT(end,1:2);
                        
                        LAYER(lnum).start_pts(course_num_to_swap,:) = LAYER(lnum).Course(course_num_to_swap).POINT(1,1:2);
                        LAYER(lnum).end_pts(course_num_to_swap,:) = LAYER(lnum).Course(course_num_to_swap).POINT(end,1:2);
                    end
                else % idx is in the first half of the list so a start point of a course was closest, no need to flip it but still to swp next and closest
                    course_num_to_swap = cnum + idx;
                    
                    temp = LAYER(lnum).Course(cnum+1);
                    LAYER(lnum).Course(cnum+1) = LAYER(lnum).Course(course_num_to_swap);
                    LAYER(lnum).Course(course_num_to_swap) = temp;
                    
                    rows_to_swap = [cnum+1, course_num_to_swap];
                
                    LAYER(lnum).start_pts(rows_to_swap,:) = LAYER(lnum).start_pts(rows_to_swap([2,1]),:);
                    LAYER(lnum).end_pts(rows_to_swap,:) = LAYER(lnum).end_pts(rows_to_swap([2,1]),:);
                
                end
%             end
            

        end
        if prtOpt.frameBool == 1 %needs to add the boundary again! 
            LAYER(lnum).Course(end+1) = layer_woBoundary(lnum).Course(end);
        end 
%     end

    end    
    layerReorder = LAYER; 
end