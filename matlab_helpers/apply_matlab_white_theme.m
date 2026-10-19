function palette = apply_matlab_white_theme()
% Replacement presentation helper. Run before the supplied s3.m as well.
palette = [0.10 0.45 0.65; 0.85 0.45 0.12; 0.30 0.65 0.40];
set(groot, 'defaultFigureColor', 'w', 'defaultAxesColor', 'w', ...
    'defaultAxesXColor', [0.2 0.2 0.2], 'defaultAxesYColor', [0.2 0.2 0.2]);
end
