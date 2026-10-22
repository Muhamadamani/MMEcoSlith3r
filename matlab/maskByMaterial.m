function layerOut = maskByMaterial(layerIn)
% MASKBYMATERIAL   Keep only bamboo/carbon courses, properly scaled.
%   Assumes these two files live in the same folder:
%     mesh_data_loops.mat  (centroids,bamboo_ids,carbon_ids,perim_loops)
%     DIM.mat              (dim = [Xmax, Ymax])
%
%   layerOut = maskByMaterial(layerIn)

  base = '/Users/mamani/Downloads/slith3r_mu_main/examples/multimaterial_matlab_output/';

  % 1) load FE support + boundary loops
  S = load(fullfile(base,'mesh_data_loops.mat'), ...
           'centroids','bamboo_ids','carbon_ids','perim_loops');
  centroids  = S.centroids;
  bamboo_ids = S.bamboo_ids;
  carbon_ids = S.carbon_ids;

  % 2) load build dimensions
  D = load(fullfile(base,'DIM.mat'),'dim');
  dims = [99.5, 39.5];       % e.g. [99.5, 39.5]
  meshXmax = dims(1);
  meshYmax = dims(2);

  % 3) find a sample ANGLES grid range from the first nonempty course
  samplePts = [];
  for L=1:numel(layerIn)
    if ~isempty(layerIn(L).Course)
      samplePts = layerIn(L).Course(1).POINT(:,1:2);
      break;
    end
  end
  if isempty(samplePts)
    layerOut = layerIn; return;
  end

  % 4) build linear map: ANGLES‐coords → [0..meshXmax]×[0..meshYmax]
  angX = samplePts(:,1);
  angY = samplePts(:,2);
  sx = meshXmax / (max(angX)-min(angX));
  sy = meshYmax / (max(angY)-min(angY));
  tx = -min(angX)*sx;
  ty = -min(angY)*sy;

  % 5) mask every course
  layerOut = layerIn;
  for L=1:numel(layerIn)
    newCourses = struct('POINT',{});
    ci = 1;
    for C=1:numel(layerIn(L).Course)
      P = layerIn(L).Course(C).POINT;  % Nx4: [X Y pad width]
      if isempty(P), continue; end

      % rescale to FE frame
      Xm = P(:,1)*sx + tx;
      Ym = P(:,2)*sy + ty;

      % check nearest‐centroid
      idx = knnsearch(centroids, [Xm,Ym]);
      keep = ismember(idx,bamboo_ids) | ismember(idx,carbon_ids);

      if any(keep)
        newCourses(ci).POINT = P(keep,:);
        ci = ci+1;
      end
    end
    layerOut(L).Course = newCourses;
  end
end
