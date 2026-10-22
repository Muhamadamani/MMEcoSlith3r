function layerMoved = movePrint(layer,startpos,swap)
    % startpos -- start position [xmin ymin] which should be added to all
    % points. If the layer has negative data this must be taken into
    % account 
    % swap -- a bool to swap x and y if necessary 
    nLayer = size(layer,2);
    layerMoved = layer; 
        for layer_num = 1:nLayer
        
            ncourses = size(layer(layer_num).Course,2);            
            for course_num = 1:ncourses
                if swap == 1 
                    layerMoved(layer_num).Course(course_num).POINT(:,1) = layer(layer_num).Course(course_num).POINT(:,2) + startpos(1); 
                    layerMoved(layer_num).Course(course_num).POINT(:,2) = layer(layer_num).Course(course_num).POINT(:,1) + startpos(2); 
                else
                    layerMoved(layer_num).Course(course_num).POINT(:,1) = layer(layer_num).Course(course_num).POINT(:,1) + startpos(1); 
                    layerMoved(layer_num).Course(course_num).POINT(:,2) = layer(layer_num).Course(course_num).POINT(:,2) + startpos(2); 
                end

            end

        end
end