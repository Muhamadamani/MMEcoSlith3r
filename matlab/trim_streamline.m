function trimmed_pts = trim_streamline(all_streamlines, current_streamline, dist_tol)

if isempty(all_streamlines)
    trimmed_pts = current_streamline;
else
    dists = pdist2(all_streamlines, current_streamline, 'euclidean');
    % find first instance of dists < tol along the current_streamline
    aa = dists <= dist_tol;
    
    dist_ind = prod(~aa);
    
    cut_off = find(~dist_ind,1);
    
    if isempty(cut_off)
        trimmed_pts = current_streamline(:,:);
    else
        trimmed_pts = current_streamline(1:cut_off,:);
    end
end

end