function segmented = kdSegmentCourses(layerReorder, prtOpt)
    % build list of all course points + index back to course
    allPts = []; courseIdx = [];
    for c = 1:numel(layerReorder(1).Course)
        P = layerReorder(1).Course(c).POINT(:,1:2);
        allPts    = [allPts;    P];
        courseIdx = [courseIdx; repmat(c,size(P,1),1)];
    end

    % make KD-trees from centroids
    bambooTree = KDTreeSearcher(prtOpt.bambooPts);
    carbonTree = KDTreeSearcher(prtOpt.carbonPts);

    % nearest-neighbor for every course point
    [~,dB] = knnsearch(bambooTree, allPts);
    [~,dC] = knnsearch(carbonTree, allPts);
    isBamboo = dB <= dC;

    % build output struct
    segmented = layerReorder;  % copy shape
    for c = 1:numel(layerReorder(1).Course)
        idx = find(courseIdx == c);
        P   = layerReorder(1).Course(c).POINT;
        mask = isBamboo(idx);
        segmented(1).Course(c).bamboo.POINT = P(mask,:);
        segmented(1).Course(c).carbon.POINT = P(~mask,:);
    end
end
