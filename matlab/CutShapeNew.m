function layerTrim = CutShapeNew(layer, ANGLES, dim, prtOpt)
    binaryImage = rgb2gray(prtOpt.I) ./ 255;
    [B, ~, ~] = bwboundaries(binaryImage);

    [Iy, Ix] = size(binaryImage);  % image dimensions

    % Extract ANGLES bounds for scaling
    allX = [ANGLES.X]; allY = [ANGLES.Y];
    minX = min(allX(:)); maxX = max(allX(:));
    minY = min(allY(:)); maxY = max(allY(:));

    % Scale boundary for visualization reference
    boundary = B{1};
    boundary_scale = [ ...
        (boundary(:,2) / Ix) * (maxX - minX) + minX, ...
        (1 - boundary(:,1) / Iy) * (maxY - minY) + minY ...
    ];

    nLayer = length(ANGLES);
    for numLayer = 1:nLayer
        ncourses = numel(layer(numLayer).Course);
        mem_course = 0;

        for numCourse = 1:ncourses
            pts = layer(numLayer).Course(numCourse).POINT;
            if isempty(pts)
                continue
            end

            x = pts(:,1);
            y = pts(:,2);
            width = pts(:,4);

            % Map to image coordinates — flip Y only
            xIm = round((x - minX) / (maxX - minX) * (Ix - 1)) + 1;
            yIm = Iy - round((y - minY) / (maxY - minY) * (Iy - 1));

            % Safety clipping
            xIm = min(max(xIm, 1), Ix);
            yIm = min(max(yIm, 1), Iy);

            % Filter points inside the mask
            xnew = []; ynew = []; widthnew = [];
            previousfilled = false;

            for iPt = 1:length(x)
                mask = binaryImage(yIm(iPt), xIm(iPt));
                if mask == 1
                    xnew = [xnew; x(iPt)];
                    ynew = [ynew; y(iPt)];
                    widthnew = [widthnew; width(iPt)];
                    previousfilled = true;
                elseif mask == 0 && previousfilled
                    xnew = [xnew; NaN];
                    ynew = [ynew; NaN];
                    widthnew = [widthnew; NaN];
                    previousfilled = false;
                end
            end

            if ~isempty(xnew)
                interrupt = find(isnan(xnew));
                interrupt(interrupt == length(xnew)) = [];
                lastix = 1;

                if ~isempty(interrupt)
                    for iStop = 1:(length(interrupt)+1)
                        if iStop <= length(interrupt)
                            index_trim = lastix:interrupt(iStop)-1;
                            lastix = interrupt(iStop)+1;
                        else
                            index_trim = lastix:length(xnew);
                        end

                        if length(index_trim) > 2
                            mem_course = mem_course + 1;
                            layerTrim(numLayer).Course(mem_course).POINT = ...
                                [xnew(index_trim), ynew(index_trim), ...
                                 ones(length(index_trim),1), widthnew(index_trim)];
                        end
                    end
                else
                    mem_course = mem_course + 1;
                    layerTrim(numLayer).Course(mem_course).POINT = ...
                        [xnew, ynew, ones(length(xnew),1), widthnew];
                end
            end
        end

        % Add outer boundary as visual reference course (optional)
            %Alex: We do not want the edge
        % 
        % pol = [boundary_scale(:,1), boundary_scale(:,2)];
        % [ps, ~] = dpsimplify(pol, prtOpt.tol * 5);
        % mem_course = mem_course + 1;
        % layerTrim(numLayer).Course(mem_course).POINT = ...
        %     [ps(:,1), ps(:,2), ones(size(ps,1),1), ...
        %      (prtOpt.upperbound/2)*ones(size(ps,1),1)];
    end
end
