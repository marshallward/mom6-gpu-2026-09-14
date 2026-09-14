size(300);

real dx = 2.0;
real dy = 3.3;
real dz = 3.0;

int ni = 2;
int nj = 1;
int nk = 1;

pair iso(triple p)
{
    return (
        p.x - p.y,
        p.z + 0.5*(p.x + p.y)
    );
}

void edge(triple a, triple b)
{
    draw(iso(a)--iso(b), black+linewidth(0.8));
}

path face(triple a, triple b, triple c, triple d)
{
    return iso(a)--iso(b)--iso(c)--iso(d)--cycle;
}

pen faceFill = rgb(0.95,0.65,0.15)+opacity(0.55);
fill(face((0,0,0), (ni*dx,0,0), (ni*dx,nj*dy,0), (0,nj*dy,0)), faceFill);
fill(face((0,0,0), (0,nj*dy,0), (0,nj*dy,nk*dz), (0,0,nk*dz)), faceFill);
fill(face((0,0,0), (ni*dx,0,0), (ni*dx,0,nk*dz), (0,0,nk*dz)), faceFill);
fill(face((ni*dx,0,0), (ni*dx,nj*dy,0), (ni*dx,nj*dy,nk*dz), (ni*dx,0,nk*dz)), faceFill);
fill(face((0,nj*dy,0), (ni*dx,nj*dy,0), (ni*dx,nj*dy,nk*dz), (0,nj*dy,nk*dz)), faceFill);
fill(face((0,0,nk*dz), (ni*dx,0,nk*dz), (ni*dx,nj*dy,nk*dz), (0,nj*dy,nk*dz)), faceFill);

// i-direction
for (int j=0; j<=nj; ++j)
for (int k=0; k<=nk; ++k)
    edge((0,j*dy,k*dz), (ni*dx,j*dy,k*dz));

// j-direction
for (int i=0; i<=ni; ++i) {
if (i == 1) continue;
for (int k=0; k<=nk; ++k)
    edge((i*dx,0,k*dz), (i*dx,nj*dy,k*dz));
}

// k-direction
for (int i=0; i<=ni; ++i) {
if (i == 1) continue;
for (int j=0; j<=nj; ++j)
    edge((i*dx,j*dy,0), (i*dx,j*dy,nk*dz));
}
