function update_usv_patch(handle, x, y, psi, scale)
vertices = [10 0; 2 3; -6 3; -6 -3; 2 -3] * scale;
rotation = [cos(psi) -sin(psi); sin(psi) cos(psi)];
world = (rotation * vertices')' + [x y];
set(handle, 'XData', world(:,1), 'YData', world(:,2));
end
