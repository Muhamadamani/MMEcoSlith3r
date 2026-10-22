function plot_circ(x, y, r, lw)
    t = linspace(0, 2*pi, 100);
%     t = t(1:end-1);
    plot(x+r*cos(t), y+r*sin(t), 'LineWidth', lw);
end