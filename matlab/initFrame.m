function outer = initFrame(ANGLES,i,bandwidth)
    X = ANGLES(i).X; Y = ANGLES(i).Y; 

    minx = min(X,[],"all");          miny = min(Y,[],"all");       
    Lx = max(X,[],"all") - minx;     Ly = max(Y,[],"all") - miny;

    %edges of the domain +/- a small amount in order to make sure
    %streamlines are always seeded inside the domain
    bw = bandwidth/100;
    le = -bw+minx;
    re = minx+Lx+bw;
    te = miny+Ly+bw;
    be = miny-bw;

    vx = linspace(le, re, Lx+1);
    vy = linspace(be, te, Ly+1);

    [Vx, Vy] = meshgrid(vx,vy);

    %frame only
    vv = [Vx(:), Vy(:)];
    outer = vv(vv(:,1) == le | vv(:,1) == re |...
            vv(:,2) == be | vv(:,2) == te, :);

end
