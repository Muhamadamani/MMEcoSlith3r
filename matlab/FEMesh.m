function layerMasked = FEMesh(layer, prtOpt)
% FEMesh   Mask each layer’s courses to the FE‐mesh region and true boundary loops.
%
%   layerMasked = FEMesh(layer, prtOpt)
%   Applies both the centroid+radius test AND an inpolygon test against
%   your perim_loops (outer boundary + any holes).

  %--- 1) load FE support + geometry loops ---
  baseFolder = '/Users/mamani/Downloads/slith3r_mu_main/examples/multimaterial_matlab_output/';
  M = load(fullfile(baseFolder,'mesh_data_loops.mat'), ...
           'centroids','bamboo_ids','carbon_ids','perim_loops');
  centroids   = M.centroids;
  bamboo_ids  = M.bamboo_ids;
  carbon_ids  = M.carbon_ids;
  loops       = M.perim_loops;       % cell array of N×2 loops
  material_radius = prtOpt.threshDist;

  % identify outer loop vs holes by area
  areas = cellfun(@(c) polyarea(c(:,1), c(:,2)), loops);
  [~, Iouter] = max(areas);
  outer = loops{Iouter};
  holes = loops(setdiff(1:numel(loops), Iouter));

  %--- 2) mask each course point-by-point ---
  layerMasked = layer;
  for L = 1:numel(layer)
    newCourses = struct('POINT',{});  
    ci = 1;
    for C = 1:numel(layer(L).Course)
      pts = layer(L).Course(C).POINT;  % Nx4: [X,Y, pad, width]
      if isempty(pts), continue; end

      % a) FE‐mesh distance+ID mask
      [idx, d] = knnsearch(centroids, pts(:,1:2));
      feKeep = (d < material_radius) & ...
               (ismember(idx, bamboo_ids) | ismember(idx, carbon_ids));

      % b) in‐outer‐loop & outside‐holes mask
      inOuter = inpolygon(pts(:,1), pts(:,2), outer(:,1), outer(:,2));
      inHole  = false(size(inOuter));
      for h = 1:numel(holes)
        inHole = inHole | inpolygon(pts(:,1), pts(:,2), ...
                                     holes{h}(:,1), holes{h}(:,2));
      end

      keep = feKeep & inOuter & ~inHole;
      if any(keep)
        newCourses(ci).POINT = pts(keep, :);
        ci = ci + 1;
      end
    end
    layerMasked(L).Course = newCourses;
  end
end
