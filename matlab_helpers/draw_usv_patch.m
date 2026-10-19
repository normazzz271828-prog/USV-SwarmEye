function handle = draw_usv_patch(x, y, psi, color, scale)
% Replacement ship glyph; headings are radians from east.
vertices = [10 0; 2 3; -6 3; -6 -3; 2 -3] * scale;
rotation = [cos(psi) -sin(psi); sin(psi) cos(psi)];
world = (rotation * vertices')' + [x y];
handle = patch(world(:,1), world(:,2), color, 'EdgeColor', color);
end
