function smooth_loops = smoothBoundary(loops, nPtsPerSeg)
% SMOOTHBOUNDARY   Fit a smooth cubic spline to each polygonal loop.
%   smooth_loops = smoothBoundary(loops, nPtsPerSeg)
%
%   loops         : cell array of K×2 closed‐polygon vertex lists.
%   nPtsPerSeg    : # of spline points to generate *per original edge*.
%
%   Returns the same cell array size, but each loop{k} is replaced by
%   a smooth version with nPtsPerSeg*(#edges) points.
    if nargin<2, nPtsPerSeg = 8; end
    smooth_loops = cell(size(loops));
    for k = 1:numel(loops)
        P = loops{k};
        % enforce closed
        if ~isequal(P(1,:),P(end,:))
            P(end+1,:) = P(1,:);
        end
        % parametrize by chord-length
        t = [0; cumsum( sqrt( sum(diff(P,1,1).^2, 2) ) )];
        % splines for x(t), y(t)
        spx = spline(t, P(:,1));
        spy = spline(t, P(:,2));
        % fine sampling
        Tq = linspace(0, t(end), nPtsPerSeg*(numel(t)-1)+1)';
        Xq = ppval(spx, Tq);
        Yq = ppval(spy, Tq);
        smooth_loops{k} = [Xq(:), Yq(:)];
    end
end
