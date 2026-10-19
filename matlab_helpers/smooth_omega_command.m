function omega = smooth_omega_command(raw, previous, dt, tau, max_rate, max_omega)
% Reconstructed helper; not the missing author's implementation.
% Backward Euler low-pass, slew-rate limit, then angular-speed saturation.
validateattributes(raw, {'numeric'}, {'scalar','real','finite'});
validateattributes(previous, {'numeric'}, {'scalar','real','finite'});
validateattributes(dt, {'numeric'}, {'scalar','positive','finite'});
validateattributes(tau, {'numeric'}, {'scalar','positive','finite'});
validateattributes(max_rate, {'numeric'}, {'scalar','positive','finite'});
validateattributes(max_omega, {'numeric'}, {'scalar','positive','finite'});
target = max(-max_omega, min(max_omega, raw));
previous = max(-max_omega, min(max_omega, previous));
filtered = previous + dt / (tau + dt) * (target - previous);
increment = max(-max_rate * dt, min(max_rate * dt, filtered - previous));
omega = max(-max_omega, min(max_omega, previous + increment));
end
