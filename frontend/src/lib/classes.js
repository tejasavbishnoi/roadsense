// Display info for each damage class. Colours match backend/app/main.py.
export const CLASSES = {
  pothole: {
    name: 'Pothole',
    color: '#EF4D4D',
    code: 'D40',
    about: 'A bowl-shaped hole where the surface has broken away.',
  },
  alligator_crack: {
    name: 'Alligator crack',
    color: '#F97316',
    code: 'D20',
    about: 'A web of connected cracks. The layer underneath is failing.',
  },
  transverse_crack: {
    name: 'Transverse crack',
    color: '#E5B300',
    code: 'D10',
    about: 'A crack running across the road, often from temperature changes.',
  },
  longitudinal_crack: {
    name: 'Longitudinal crack',
    color: '#0EA5C6',
    code: 'D00',
    about: 'A crack running along the direction of traffic.',
  },
}

export const CLASS_ORDER = ['pothole', 'alligator_crack', 'transverse_crack', 'longitudinal_crack']

export const classInfo = (label) =>
  CLASSES[label] ?? { name: label.replace(/_/g, ' '), color: '#8A94A0', code: '', about: '' }

export const LEVEL_COLORS = {
  Good: '#2F9E62',
  Fair: '#D9A400',
  Poor: '#E8701A',
  Critical: '#D93636',
}
