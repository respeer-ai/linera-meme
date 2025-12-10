import axios, { type AxiosInstance } from 'axios'

const createAPI = (url: string): AxiosInstance | undefined => {
  return axios.create({
    baseURL: url,
    withCredentials: false,
    responseType: 'json',
    timeout: 60000
  })
}

export { createAPI }
